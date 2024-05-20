import vegaEmbed from "https://esm.sh/vega-embed@6?deps=vega@5&deps=vega-lite@5.17.0";
import lodashDebounce from "https://esm.sh/lodash-es@4.17.21/debounce";

// Note: For offline support, the import lines above are removed and the remaining script
// is bundled using vl-convert's javascript_bundle function. See the documentation of
// the javascript_bundle function for details on the available imports and their names.
// If an additional import is required in the future, it will need to be added to vl-convert
// in order to preserve offline support.
async function render({ model, el }) {
    let finalize;

    function showError(error){
        el.innerHTML = (
            '<div style="color:red;">'
            + '<p>JavaScript Error: ' + error.message + '</p>'
            + "<p>This usually means there's a typo in your chart specification. "
            + "See the javascript console for the full traceback.</p>"
            + '</div>'
        );
    }

    const reembed = async () => {
        if (finalize != null) {
          finalize();
        }

        model.set("local_tz", Intl.DateTimeFormat().resolvedOptions().timeZone);

        let spec = structuredClone(model.get("spec"));
        if (spec == null) {
            // Remove any existing chart and return
            while (el.firstChild) {
                el.removeChild(el.lastChild);
            }
            model.save_changes();
            return;
        }
        let embedOptions = structuredClone(model.get("embed_options")) ?? undefined;

        let api;
        try {
            api = await vegaEmbed(el, spec, embedOptions);
        } catch (error) {
            showError(error)
            return;
        }

        finalize = api.finalize;

        // Debounce config
        const wait = model.get("debounce_wait") ?? 10;
        const debounceOpts = {leading: false, trailing: true};
        if (model.get("max_wait") ?? true) {
            debounceOpts["maxWait"] = wait;
        }

        const initialSelections = {};
        for (const selectionName of Object.keys(model.get("_vl_selections"))) {
            const storeName = `${selectionName}_store`;
            const selectionHandler = (_, value) => {
                const newSelections = cleanJson(model.get("_vl_selections") ?? {});
                const store = cleanJson(api.view.data(storeName) ?? []);

                newSelections[selectionName] = {value, store};
                model.set("_vl_selections", newSelections);
                model.save_changes();
            };
            api.view.addSignalListener(selectionName, lodashDebounce(selectionHandler, wait, debounceOpts));

            initialSelections[selectionName] = {
                value: cleanJson(api.view.signal(selectionName) ?? {}),
                store: cleanJson(api.view.data(storeName) ?? [])
            }
        }
        model.set("_vl_selections", initialSelections);

        const initialParams = {};
        for (const paramName of Object.keys(model.get("_params"))) {
            const paramHandler = (_, value) => {
                const newParams = JSON.parse(JSON.stringify(model.get("_params"))) || {};
                newParams[paramName] = value;
                model.set("_params", newParams);
                model.save_changes();
            };
            api.view.addSignalListener(paramName, lodashDebounce(paramHandler, wait, debounceOpts));

            initialParams[paramName] = api.view.signal(paramName) ?? null
        }
        model.set("_params", initialParams);
        model.save_changes();

        // Param change callback
        model.on('change:_params', async (new_params) => {
            for (const [param, value] of Object.entries(new_params.changed._params)) {
                api.view.signal(param, value);
            }
            await api.view.runAsync();
        });

        // Add signal/data listeners
        for (const watch of model.get("_js_watch_plan") ?? []) {
            if (watch.namespace === "data") {
                const dataHandler = (_, value) => {
                    model.set("_js_to_py_updates", [{
                        namespace: "data",
                        name: watch.name,
                        scope: watch.scope,
                        value: cleanJson(value)
                    }]);
                    model.save_changes();
                };
                addDataListener(api.view, watch.name, watch.scope, lodashDebounce(dataHandler, wait, debounceOpts))

            } else if (watch.namespace === "signal") {
                const signalHandler = (_, value) => {
                    model.set("_js_to_py_updates", [{
                        namespace: "signal",
                        name: watch.name,
                        scope: watch.scope,
                        value: cleanJson(value)
                    }]);
                    model.save_changes();
                };

                addSignalListener(api.view, watch.name, watch.scope, lodashDebounce(signalHandler, wait, debounceOpts))
            }
        }

        // Add signal/data updaters
        model.on('change:_py_to_js_updates', async (updates) => {
            for (const update of updates.changed._py_to_js_updates ?? []) {
                if (update.namespace === "signal") {
                    setSignalValue(api.view, update.name, update.scope, update.value);
                } else if (update.namespace === "data") {
                    setDataValue(api.view, update.name, update.scope, update.value);
                }
            }
            await api.view.runAsync();
        });
    }

    model.on('change:spec', reembed);
    model.on('change:embed_options', reembed);
    model.on('change:debounce_wait', reembed);
    model.on('change:max_wait', reembed);
    await reembed();
}

function cleanJson(data) {
    return JSON.parse(JSON.stringify(data))
}

function getNestedRuntime(view, scope) {
    var runtime = view._runtime;
    for (const index of scope) {
        runtime = runtime.subcontext[index];
    }
    return runtime
}

function lookupSignalOp(view, name, scope) {
    let parent_runtime = getNestedRuntime(view, scope);
    return parent_runtime.signals[name] ?? null;
}

function dataRef(view, name, scope) {
    let parent_runtime = getNestedRuntime(view, scope);
    return parent_runtime.data[name];
}

export function setSignalValue(view, name, scope, value) {
    let signal_op = lookupSignalOp(view, name, scope);
    view.update(signal_op, value);
}

export function setDataValue(view, name, scope, value) {
    let dataset = dataRef(view, name, scope);
    let changeset = view.changeset().remove(() => true).insert(value)
    dataset.modified = true;
    view.pulse(dataset.input, changeset);
}

export function addSignalListener(view, name, scope, handler) {
    let signal_op = lookupSignalOp(view, name, scope);
    return addOperatorListener(
        view,
        name,
        signal_op,
        handler,
    );
}

export function addDataListener(view, name, scope, handler) {
    let dataset = dataRef(view, name, scope).values;
    return addOperatorListener(
        view,
        name,
        dataset,
        handler,
    );
}

// Private helpers from Vega for dealing with nested signals/data
function findOperatorHandler(op, handler) {
    const h = (op._targets || [])
        .filter(op => op._update && op._update.handler === handler);
    return h.length ? h[0] : null;
}

function addOperatorListener(view, name, op, handler) {
    let h = findOperatorHandler(op, handler);
    if (!h) {
        h = trap(view, () => handler(name, op.value));
        h.handler = handler;
        view.on(op, null, h);
    }
    return view;
}

function trap(view, fn) {
    return !fn ? null : function() {
        try {
            fn.apply(this, arguments);
        } catch (error) {
            view.error(error);
        }
    };
}

export default { render }
