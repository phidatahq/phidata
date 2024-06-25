from dataclasses import dataclass
from typing import List, Dict, Any, NewType, Optional


# Type representing the "{selection}_store" dataset that corresponds to a
# Vega-Lite selection
Store = NewType("Store", List[Dict[str, Any]])


@dataclass(frozen=True, eq=True)
class IndexSelection:
    """
    An IndexSelection represents the state of an Altair
    point selection (as constructed by alt.selection_point())
    when neither the fields nor encodings arguments are specified.

    The value field is a list of zero-based indices into the
    selected dataset.

    Note: These indices only apply to the input DataFrame
    for charts that do not include aggregations (e.g. a scatter chart).
    """

    name: str
    value: List[int]
    store: Store

    @staticmethod
    def from_vega(name: str, signal: Optional[Dict[str, dict]], store: Store):
        """
        Construct an IndexSelection from the raw Vega signal and dataset values.

        Parameters
        ----------
        name: str
            The selection's name
        signal: dict or None
            The value of the Vega signal corresponding to the selection
        store: list
            The value of the Vega dataset corresponding to the selection.
            This dataset is named "{name}_store" in the Vega view.

        Returns
        -------
        IndexSelection
        """
        if signal is None:
            indices = []
        else:
            points = signal.get("vlPoint", {}).get("or", [])
            indices = [p["_vgsid_"] - 1 for p in points]
        return IndexSelection(name=name, value=indices, store=store)


@dataclass(frozen=True, eq=True)
class PointSelection:
    """
    A PointSelection represents the state of an Altair
    point selection (as constructed by alt.selection_point())
    when the fields or encodings arguments are specified.

    The value field is a list of dicts of the form:
        [{"dim1": 1, "dim2": "A"}, {"dim1": 2, "dim2": "BB"}]

    where "dim1" and "dim2" are dataset columns and the dict values
    correspond to the specific selected values.
    """

    name: str
    value: List[Dict[str, Any]]
    store: Store

    @staticmethod
    def from_vega(name: str, signal: Optional[Dict[str, dict]], store: Store):
        """
        Construct a PointSelection from the raw Vega signal and dataset values.

        Parameters
        ----------
        name: str
            The selection's name
        signal: dict or None
            The value of the Vega signal corresponding to the selection
        store: list
            The value of the Vega dataset corresponding to the selection.
            This dataset is named "{name}_store" in the Vega view.

        Returns
        -------
        PointSelection
        """
        if signal is None:
            points = []
        else:
            points = signal.get("vlPoint", {}).get("or", [])
        return PointSelection(name=name, value=points, store=store)


@dataclass(frozen=True, eq=True)
class IntervalSelection:
    """
    An IntervalSelection represents the state of an Altair
    interval selection (as constructed by alt.selection_interval()).

    The value field is a dict of the form:
        {"dim1": [0, 10], "dim2": ["A", "BB", "CCC"]}

    where "dim1" and "dim2" are dataset columns and the dict values
    correspond to the selected range.
    """

    name: str
    value: Dict[str, list]
    store: Store

    @staticmethod
    def from_vega(name: str, signal: Optional[Dict[str, list]], store: Store):
        """
        Construct an IntervalSelection from the raw Vega signal and dataset values.

        Parameters
        ----------
        name: str
            The selection's name
        signal: dict or None
            The value of the Vega signal corresponding to the selection
        store: list
            The value of the Vega dataset corresponding to the selection.
            This dataset is named "{name}_store" in the Vega view.

        Returns
        -------
        PointSelection
        """
        if signal is None:
            signal = {}
        return IntervalSelection(name=name, value=signal, store=store)
