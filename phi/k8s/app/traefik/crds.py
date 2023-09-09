from phi.k8s.create.apiextensions_k8s_io.v1.custom_resource_definition import (
    CreateCustomResourceDefinition,
    CustomResourceDefinitionNames,
    CustomResourceDefinitionVersion,
    V1JSONSchemaProps,
)

######################################################
## Traefik CRDs
######################################################
traefik_name = "traefik"
ingressroute_crd = CreateCustomResourceDefinition(
    crd_name="ingressroutes.traefik.containo.us",
    app_name=traefik_name,
    group="traefik.containo.us",
    names=CustomResourceDefinitionNames(
        kind="IngressRoute",
        list_kind="IngressRouteList",
        plural="ingressroutes",
        singular="ingressroute",
    ),
    annotations={
        "controller-gen.kubebuilder.io/version": "v0.6.2",
    },
    versions=[
        CustomResourceDefinitionVersion(
            name="v1alpha1",
            served=True,
            storage=True,
            open_apiv3_schema=V1JSONSchemaProps(
                description="IngressRoute is an Ingress CRD specification.",
                type="object",
                required=["metadata", "spec"],
                properties={
                    "apiVersion": V1JSONSchemaProps(
                        description="APIVersion defines the versioned schema of this representation of an object. Servers should convert recognized schemas to the latest internal value, and may reject unrecognized values. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#resources",
                        type="string",
                    ),
                    "kind": V1JSONSchemaProps(
                        description="Kind is a string value representing the REST resource this object represents. Servers may infer this from the endpoint the client submits requests to. Cannot be updated. In CamelCase. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#types-kinds",
                        type="string",
                    ),
                    "metadata": V1JSONSchemaProps(type="object"),
                    "spec": V1JSONSchemaProps(
                        description="IngressRouteSpec is a specification for a IngressRouteSpec resource.",
                        type="object",
                        required=["routes"],
                        properties={
                            "entryPoints": V1JSONSchemaProps(
                                type="array",
                                items={
                                    "type": "string",
                                },
                            ),
                            "routes": V1JSONSchemaProps(
                                type="array",
                                items={
                                    "description": "Route contains the set of routes.",
                                    "type": "object",
                                    "required": ["kind", "match"],
                                    "properties": {
                                        "kind": V1JSONSchemaProps(type="string", enum=["Rule"]),
                                        "match": V1JSONSchemaProps(
                                            type="string",
                                        ),
                                        "middlewares": V1JSONSchemaProps(
                                            type="array",
                                            items={
                                                "description": "Route contains the set of routes.",
                                                "type": "object",
                                                "required": ["name"],
                                                "properties": {
                                                    "name": V1JSONSchemaProps(
                                                        type="string",
                                                    ),
                                                    "namespace": V1JSONSchemaProps(
                                                        type="string",
                                                    ),
                                                },
                                            },
                                        ),
                                        "priority": V1JSONSchemaProps(
                                            type="integer",
                                        ),
                                        "services": V1JSONSchemaProps(
                                            type="array",
                                            items={
                                                "description": "Service defines an upstream to proxy traffic.",
                                                "type": "object",
                                                "required": ["name"],
                                                "properties": {
                                                    "kind": V1JSONSchemaProps(
                                                        type="string",
                                                        enum=[
                                                            "Service",
                                                            "TraefikService",
                                                        ],
                                                    ),
                                                    "name": V1JSONSchemaProps(
                                                        description="Name is a reference to a Kubernetes Service object (for a load-balancer of servers), or to a TraefikServic                               object (service load-balancer, mirroring, etc). The differentiation between the two is specified in the Kind field.",
                                                        type="string",
                                                    ),
                                                    "passHostHeader": V1JSONSchemaProps(
                                                        type="boolean",
                                                    ),
                                                    "port": V1JSONSchemaProps(
                                                        any_of=[
                                                            V1JSONSchemaProps(
                                                                type="integer",
                                                            ),
                                                            V1JSONSchemaProps(
                                                                type="string",
                                                            ),
                                                        ],
                                                        x_kubernetes_int_or_string=True,
                                                    ),
                                                    "responseForwarding": V1JSONSchemaProps(
                                                        description="ResponseForwarding holds configuration for the forward of the response.",
                                                        type="object",
                                                        properties={
                                                            "flushInterval": V1JSONSchemaProps(
                                                                type="string",
                                                            )
                                                        },
                                                    ),
                                                    "scheme": V1JSONSchemaProps(
                                                        type="string",
                                                    ),
                                                    "serversTransport": V1JSONSchemaProps(
                                                        type="string",
                                                    ),
                                                    "sticky": V1JSONSchemaProps(
                                                        description="Sticky holds the sticky configuration.",
                                                        type="object",
                                                        properties={
                                                            "cookie": V1JSONSchemaProps(
                                                                description="Cookie holds the sticky configuration based on cookie",
                                                                type="object",
                                                                properties={
                                                                    "httpOnly": V1JSONSchemaProps(
                                                                        type="boolean",
                                                                    ),
                                                                    "name": V1JSONSchemaProps(
                                                                        type="string",
                                                                    ),
                                                                    "sameSite": V1JSONSchemaProps(
                                                                        type="string",
                                                                    ),
                                                                    "secure": V1JSONSchemaProps(
                                                                        type="boolean",
                                                                    ),
                                                                },
                                                            )
                                                        },
                                                    ),
                                                    "strategy": V1JSONSchemaProps(
                                                        type="string",
                                                    ),
                                                    "weight": V1JSONSchemaProps(
                                                        description="Weight should only be specified when Name references a TraefikService object (and to be precise, one that embeds a Weighted Round Robin).",
                                                        type="integer",
                                                    ),
                                                },
                                            },
                                        ),
                                    },
                                },
                            ),
                            "tls": V1JSONSchemaProps(
                                description="TLS contains the TLS certificates configuration of the routes. To enable Let's Encrypt, use an empty TLS struct, e.g. in YAML: \n \t tls: {} # inline format \n \t tls: \t   secretName: # block format",
                                type="object",
                                properties={
                                    "certResolver": V1JSONSchemaProps(
                                        type="string",
                                    ),
                                    "domains": V1JSONSchemaProps(
                                        type="array",
                                        items={
                                            "description": "Domain holds a domain name with SANs.",
                                            "type": "object",
                                            "properties": {
                                                "main": V1JSONSchemaProps(
                                                    type="string",
                                                ),
                                                "sans": V1JSONSchemaProps(
                                                    type="array",
                                                    items={
                                                        "type": "string",
                                                    },
                                                ),
                                            },
                                        },
                                    ),
                                    "options": V1JSONSchemaProps(
                                        description="Options is a reference to a TLSOption, that specifies the parameters of the TLS connection.",
                                        type="object",
                                        required=["name"],
                                        properties={
                                            "name": V1JSONSchemaProps(
                                                type="string",
                                            ),
                                            "namespace": V1JSONSchemaProps(
                                                type="string",
                                            ),
                                        },
                                    ),
                                    "secretName": V1JSONSchemaProps(
                                        description="SecretName is the name of the referenced Kubernetes Secret to specify the certificate details.",
                                        type="string",
                                    ),
                                    "store": V1JSONSchemaProps(
                                        description="Store is a reference to a TLSStore, that specifies the parameters of the TLS store.",
                                        type="object",
                                        required=["name"],
                                        properties={
                                            "name": V1JSONSchemaProps(
                                                type="string",
                                            ),
                                            "namespace": V1JSONSchemaProps(
                                                type="string",
                                            ),
                                        },
                                    ),
                                },
                            ),
                        },
                    ),
                },
            ),
        )
    ],
)

ingressroutetcp_crd = CreateCustomResourceDefinition(
    crd_name="ingressroutetcps.traefik.containo.us",
    app_name=traefik_name,
    group="traefik.containo.us",
    names=CustomResourceDefinitionNames(
        kind="IngressRouteTCP",
        list_kind="IngressRouteTCPList",
        plural="ingressroutetcps",
        singular="ingressroutetcp",
    ),
    annotations={
        "controller-gen.kubebuilder.io/version": "v0.6.2",
    },
    versions=[
        CustomResourceDefinitionVersion(
            name="v1alpha1",
            open_apiv3_schema=V1JSONSchemaProps(
                description="IngressRouteTCP is an Ingress CRD specification.",
                type="object",
                required=["metadata", "spec"],
                properties={
                    "apiVersion": V1JSONSchemaProps(
                        description="APIVersion defines the versioned schema of this representation of an object. Servers should convert recognized schemas to the latest internal value, and may reject unrecognized values. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#resources",
                        type="string",
                    ),
                    "kind": V1JSONSchemaProps(
                        description="Kind is a string value representing the REST resource this object represents. Servers may infer this from the endpoint the client submits requests to. Cannot be updated. In CamelCase. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#types-kinds",
                        type="string",
                    ),
                    "metadata": V1JSONSchemaProps(type="object"),
                    "spec": V1JSONSchemaProps(
                        description="IngressRouteTCPSpec is a specification for a IngressRouteTCPSpec resource.",
                        type="object",
                        required=["routes"],
                        properties={
                            "entryPoints": V1JSONSchemaProps(
                                type="array",
                                items={
                                    "type": "string",
                                },
                            ),
                            "routes": V1JSONSchemaProps(
                                type="array",
                                items={
                                    "description": "RouteTCP contains the set of routes.",
                                    "type": "object",
                                    "required": ["match"],
                                    "properties": {
                                        "match": V1JSONSchemaProps(
                                            type="string",
                                        ),
                                        "middlewares": V1JSONSchemaProps(
                                            description="Middlewares contains references to MiddlewareTCP resources.",
                                            type="array",
                                            items={
                                                "description": "ObjectReference is a generic reference to a Traefik resource.",
                                                "type": "object",
                                                "required": ["name"],
                                                "properties": {
                                                    "name": V1JSONSchemaProps(
                                                        type="string",
                                                    ),
                                                    "namespace": V1JSONSchemaProps(
                                                        type="string",
                                                    ),
                                                },
                                            },
                                        ),
                                        "services": V1JSONSchemaProps(
                                            type="array",
                                            items={
                                                "description": "ServiceTCP defines an upstream to proxy traffic.",
                                                "type": "object",
                                                "required": ["name", "port"],
                                                "properties": {
                                                    "name": V1JSONSchemaProps(
                                                        type="string",
                                                    ),
                                                    "namespace": V1JSONSchemaProps(
                                                        type="string",
                                                    ),
                                                    "port": V1JSONSchemaProps(
                                                        any_of=[
                                                            V1JSONSchemaProps(
                                                                type="integer",
                                                            ),
                                                            V1JSONSchemaProps(
                                                                type="string",
                                                            ),
                                                        ],
                                                        x_kubernetes_int_or_string=True,
                                                    ),
                                                    "proxyProtocol": V1JSONSchemaProps(
                                                        description="ProxyProtocol holds the ProxyProtocol configuration.",
                                                        type="object",
                                                        properties={
                                                            "version": V1JSONSchemaProps(
                                                                type="integer",
                                                            )
                                                        },
                                                    ),
                                                    "terminationDelay": V1JSONSchemaProps(
                                                        type="integer",
                                                    ),
                                                    "weight": V1JSONSchemaProps(
                                                        type="integer",
                                                    ),
                                                },
                                            },
                                        ),
                                    },
                                },
                            ),
                            "tls": V1JSONSchemaProps(
                                description="TLSTCP contains the TLS certificates configuration of the routes. To enable Let's Encrypt, use an empty TLS struct, e.g. in YAML: \n \t tls: {} # inline format \n \t tls: \t   secretName: # block format",
                                type="object",
                                properties={
                                    "certResolver": V1JSONSchemaProps(
                                        type="string",
                                    ),
                                    "domains": V1JSONSchemaProps(
                                        type="array",
                                        items={
                                            "description": "Domain holds a domain name with SANs.",
                                            "type": "object",
                                            "properties": {
                                                "main": V1JSONSchemaProps(
                                                    type="string",
                                                ),
                                                "sans": V1JSONSchemaProps(
                                                    type="array",
                                                    items={
                                                        "type": "string",
                                                    },
                                                ),
                                            },
                                        },
                                    ),
                                    "options": V1JSONSchemaProps(
                                        description="Options is a reference to a TLSOption, that specifies the parameters of the TLS connection.",
                                        type="object",
                                        required=["name"],
                                        properties={
                                            "name": V1JSONSchemaProps(
                                                type="string",
                                            ),
                                            "namespace": V1JSONSchemaProps(
                                                type="string",
                                            ),
                                        },
                                    ),
                                    "passthrough": V1JSONSchemaProps(
                                        type="boolean",
                                    ),
                                    "secretName": V1JSONSchemaProps(
                                        description="SecretName is the name of the referenced Kubernetes Secret to specify the certificate details.",
                                        type="string",
                                    ),
                                    "store": V1JSONSchemaProps(
                                        description="Store is a reference to a TLSStore, that specifies the parameters of the TLS store.",
                                        type="object",
                                        required=["name"],
                                        properties={
                                            "name": V1JSONSchemaProps(
                                                type="string",
                                            ),
                                            "namespace": V1JSONSchemaProps(
                                                type="string",
                                            ),
                                        },
                                    ),
                                },
                            ),
                        },
                    ),
                },
            ),
        )
    ],
)

ingressrouteudp_crd = CreateCustomResourceDefinition(
    crd_name="ingressrouteudps.traefik.containo.us",
    app_name=traefik_name,
    group="traefik.containo.us",
    names=CustomResourceDefinitionNames(
        kind="IngressRouteUDP",
        list_kind="IngressRouteUDPList",
        plural="ingressrouteudps",
        singular="ingressrouteudp",
    ),
    annotations={
        "controller-gen.kubebuilder.io/version": "v0.6.2",
    },
    versions=[
        CustomResourceDefinitionVersion(
            name="v1alpha1",
            open_apiv3_schema=V1JSONSchemaProps(
                description="IngressRouteUDP is an Ingress CRD specification.",
                type="object",
                required=["metadata", "spec"],
                properties={
                    "apiVersion": V1JSONSchemaProps(
                        description="APIVersion defines the versioned schema of this representation of an object. Servers should convert recognized schemas to the latest internal value, and may reject unrecognized values. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#resources",
                        type="string",
                    ),
                    "kind": V1JSONSchemaProps(
                        description="Kind is a string value representing the REST resource this object represents. Servers may infer this from the endpoint the client submits requests to. Cannot be updated. In CamelCase. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#types-kinds",
                        type="string",
                    ),
                    "metadata": V1JSONSchemaProps(type="object"),
                    "spec": V1JSONSchemaProps(
                        description="IngressRouteUDPSpec is a specification for a IngressRouteUDPSpec resource.",
                        type="object",
                        required=["routes"],
                        properties={
                            "entryPoints": V1JSONSchemaProps(
                                type="array",
                                items={
                                    "type": "string",
                                },
                            ),
                            "routes": V1JSONSchemaProps(
                                type="array",
                                items={
                                    "description": "RouteUDP contains the set of routes.",
                                    "type": "object",
                                    "properties": {
                                        "services": V1JSONSchemaProps(
                                            type="array",
                                            items={
                                                "description": "ServiceUDP defines an upstream to proxy traffic.",
                                                "type": "object",
                                                "required": ["name", "port"],
                                                "properties": {
                                                    "name": V1JSONSchemaProps(
                                                        type="string",
                                                    ),
                                                    "namespace": V1JSONSchemaProps(
                                                        type="string",
                                                    ),
                                                    "port": V1JSONSchemaProps(
                                                        any_of=[
                                                            V1JSONSchemaProps(
                                                                type="integer",
                                                            ),
                                                            V1JSONSchemaProps(
                                                                type="string",
                                                            ),
                                                        ],
                                                        x_kubernetes_int_or_string=True,
                                                    ),
                                                    "weight": V1JSONSchemaProps(
                                                        type="integer",
                                                    ),
                                                },
                                            },
                                        ),
                                    },
                                },
                            ),
                        },
                    ),
                },
            ),
        )
    ],
)

middleware_crd = CreateCustomResourceDefinition(
    crd_name="middlewares.traefik.containo.us",
    app_name=traefik_name,
    group="traefik.containo.us",
    names=CustomResourceDefinitionNames(
        kind="Middleware",
        list_kind="MiddlewareList",
        plural="middlewares",
        singular="middleware",
    ),
    annotations={
        "controller-gen.kubebuilder.io/version": "v0.6.2",
    },
    versions=[
        CustomResourceDefinitionVersion(
            name="v1alpha1",
            open_apiv3_schema=V1JSONSchemaProps(
                description="Middleware is a specification for a Middleware resource.",
                type="object",
                required=["metadata", "spec"],
                properties={
                    "apiVersion": V1JSONSchemaProps(
                        description="APIVersion defines the versioned schema of this representation of an object. Servers should convert recognized schemas to the latest internal value, and may reject unrecognized values. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#resources",
                        type="string",
                    ),
                    "kind": V1JSONSchemaProps(
                        description="Kind is a string value representing the REST resource this object represents. Servers may infer this from the endpoint the client submits requests to. Cannot be updated. In CamelCase. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#types-kinds",
                        type="string",
                    ),
                    "metadata": V1JSONSchemaProps(type="object"),
                    "spec": V1JSONSchemaProps(
                        description="MiddlewareSpec holds the Middleware configuration.",
                        type="object",
                        properties={
                            "addPrefix": V1JSONSchemaProps(
                                description="AddPrefix holds the AddPrefix configuration.",
                                type="object",
                                properties={
                                    "prefix": V1JSONSchemaProps(
                                        type="string",
                                    ),
                                },
                            ),
                            "basicAuth": V1JSONSchemaProps(
                                description="BasicAuth holds the HTTP basic authentication configuration.",
                                type="object",
                                properties={
                                    "headerField": V1JSONSchemaProps(
                                        type="string",
                                    ),
                                    "realm": V1JSONSchemaProps(
                                        type="string",
                                    ),
                                    "removeHeader": V1JSONSchemaProps(
                                        type="boolean",
                                    ),
                                    "secret": V1JSONSchemaProps(
                                        type="string",
                                    ),
                                },
                            ),
                            "buffering": V1JSONSchemaProps(
                                description="Buffering holds the request/response buffering configuration.",
                                type="object",
                                properties={
                                    "maxRequestBodyBytes": V1JSONSchemaProps(
                                        format="int64",
                                        type="integer",
                                    ),
                                    "maxResponseBodyBytes": V1JSONSchemaProps(
                                        format="int64",
                                        type="integer",
                                    ),
                                    "memRequestBodyBytes": V1JSONSchemaProps(
                                        format="int64",
                                        type="integer",
                                    ),
                                    "memResponseBodyBytes": V1JSONSchemaProps(
                                        format="int64",
                                        type="integer",
                                    ),
                                    "retryExpression": V1JSONSchemaProps(
                                        type="string",
                                    ),
                                },
                            ),
                            "chain": V1JSONSchemaProps(
                                description="Chain holds a chain of middlewares.",
                                type="object",
                                properties={
                                    "middlewares": V1JSONSchemaProps(
                                        type="array",
                                        items={
                                            "description": "MiddlewareRef is a ref to the Middleware resources.",
                                            "type": "object",
                                            "required": ["name"],
                                            "properties": {
                                                "name": V1JSONSchemaProps(
                                                    type="string",
                                                ),
                                                "namespace": V1JSONSchemaProps(
                                                    type="string",
                                                ),
                                            },
                                        },
                                    ),
                                },
                            ),
                            "circuitBreaker": V1JSONSchemaProps(
                                description="CircuitBreaker holds the circuit breaker configuration.",
                                type="object",
                                properties={
                                    "expression": V1JSONSchemaProps(
                                        type="string",
                                    ),
                                },
                            ),
                            "compress": V1JSONSchemaProps(
                                description="Compress holds the compress configuration.",
                                type="object",
                                properties={
                                    "excludedContentTypes": V1JSONSchemaProps(
                                        type="array",
                                        items={
                                            "type": "string",
                                        },
                                    ),
                                    "minResponseBodyBytes": V1JSONSchemaProps(
                                        type="integer",
                                    ),
                                },
                            ),
                            "contentType": V1JSONSchemaProps(
                                description="ContentType middleware - or rather its unique `autoDetect` option - specifies whether to let the `Content-Type` header, if it has not been set by the backend, be automatically set to a value derived from the contents of the response. As a proxy, the default behavior should be to leave the header alone, regardless of what the backend did with it. However, the historic default was to always auto-detect and set the header if it was nil, and it is going to be kept that way in order to support users currently relying on it. This middleware exists to enable the correct behavior until at least the default one can be changed in a future version.",
                                type="object",
                                properties={
                                    "autoDetect": V1JSONSchemaProps(
                                        type="boolean",
                                    ),
                                },
                            ),
                            "digestAuth": V1JSONSchemaProps(
                                description="DigestAuth holds the Digest HTTP authentication configuration.",
                                type="object",
                                properties={
                                    "headerField": V1JSONSchemaProps(
                                        type="string",
                                    ),
                                    "realm": V1JSONSchemaProps(
                                        type="string",
                                    ),
                                    "removeHeader": V1JSONSchemaProps(
                                        type="boolean",
                                    ),
                                    "secret": V1JSONSchemaProps(
                                        type="string",
                                    ),
                                },
                            ),
                            "errors": V1JSONSchemaProps(
                                description="ErrorPage holds the custom error page configuration.",
                                type="object",
                                properties={
                                    "query": V1JSONSchemaProps(
                                        type="string",
                                    ),
                                    "service": V1JSONSchemaProps(
                                        description="Service defines an upstream to proxy traffic.",
                                        type="object",
                                        required=["name"],
                                        properties={
                                            "kind": V1JSONSchemaProps(
                                                type="string",
                                                enum=["Service", "TraefikService"],
                                            ),
                                            "name": V1JSONSchemaProps(
                                                description="Name is a reference to a Kubernetes Service object (for a load-balancer of servers), or to a TraefikServic                               object (service load-balancer, mirroring, etc). The differentiation between the two is specified in the Kind field.",
                                                type="string",
                                            ),
                                            "namespace": V1JSONSchemaProps(
                                                type="string",
                                            ),
                                            "passHostHeader": V1JSONSchemaProps(
                                                type="boolean",
                                            ),
                                            "port": V1JSONSchemaProps(
                                                any_of=[
                                                    V1JSONSchemaProps(
                                                        type="integer",
                                                    ),
                                                    V1JSONSchemaProps(
                                                        type="string",
                                                    ),
                                                ],
                                                x_kubernetes_int_or_string=True,
                                            ),
                                            "responseForwarding": V1JSONSchemaProps(
                                                description="ResponseForwarding holds configuration for the forward of the response.",
                                                type="object",
                                                properties={
                                                    "flushInterval": V1JSONSchemaProps(
                                                        type="string",
                                                    )
                                                },
                                            ),
                                            "scheme": V1JSONSchemaProps(
                                                type="string",
                                            ),
                                            "serversTransport": V1JSONSchemaProps(
                                                type="string",
                                            ),
                                            "sticky": V1JSONSchemaProps(
                                                description="Sticky holds the sticky configuration.",
                                                type="object",
                                                properties={
                                                    "cookie": V1JSONSchemaProps(
                                                        description="Cookie holds the sticky configuration based on cookie",
                                                        type="object",
                                                        properties={
                                                            "httpOnly": V1JSONSchemaProps(
                                                                type="boolean",
                                                            ),
                                                            "name": V1JSONSchemaProps(
                                                                type="string",
                                                            ),
                                                            "sameSite": V1JSONSchemaProps(
                                                                type="string",
                                                            ),
                                                            "secure": V1JSONSchemaProps(
                                                                type="boolean",
                                                            ),
                                                        },
                                                    )
                                                },
                                            ),
                                            "strategy": V1JSONSchemaProps(
                                                type="string",
                                            ),
                                            "weight": V1JSONSchemaProps(
                                                description="Weight should only be specified when Name references a TraefikService object (and to be precise, one that embeds a Weighted Round Robin).",
                                                type="integer",
                                            ),
                                        },
                                    ),
                                    "status": V1JSONSchemaProps(
                                        type="array",
                                        items={
                                            "type": "string",
                                        },
                                    ),
                                },
                            ),
                            "forwardAuth": V1JSONSchemaProps(
                                description="ForwardAuth holds the http forward authentication configuration.",
                                type="object",
                                properties={
                                    "address": V1JSONSchemaProps(
                                        type="string",
                                    ),
                                    "authRequestHeaders": V1JSONSchemaProps(
                                        type="array",
                                        items={
                                            "type": "string",
                                        },
                                    ),
                                    "authResponseHeaders": V1JSONSchemaProps(
                                        type="array",
                                        items={
                                            "type": "string",
                                        },
                                    ),
                                    "authResponseHeadersRegex": V1JSONSchemaProps(
                                        type="string",
                                    ),
                                    "tls": V1JSONSchemaProps(
                                        description="ClientTLS holds TLS specific configurations as client.",
                                        type="object",
                                        properties={
                                            "caOptional": V1JSONSchemaProps(
                                                type="string",
                                            ),
                                            "caSecret": V1JSONSchemaProps(
                                                type="string",
                                            ),
                                            "certSecret": V1JSONSchemaProps(
                                                type="string",
                                            ),
                                            "insecureSkipVerify": V1JSONSchemaProps(
                                                type="boolean",
                                            ),
                                        },
                                    ),
                                    "trustForwardHeader": V1JSONSchemaProps(
                                        type="boolean",
                                    ),
                                },
                            ),
                            "headers": V1JSONSchemaProps(
                                description="Headers holds the custom header configuration.",
                                type="object",
                                properties={
                                    "accessControlAllowCredentials": V1JSONSchemaProps(
                                        description="AccessControlAllowCredentials is only valid if true. false is ignored.",
                                        type="boolean",
                                    ),
                                    "accessControlAllowHeaders": V1JSONSchemaProps(
                                        description="AccessControlAllowHeaders must be used in response to a preflight request with Access-Control-Request-Headers set.",
                                        type="array",
                                        items={
                                            "type": "string",
                                        },
                                    ),
                                    "accessControlAllowMethods": V1JSONSchemaProps(
                                        type="array",
                                        items={
                                            "type": "string",
                                        },
                                    ),
                                    "accessControlAllowOriginList": V1JSONSchemaProps(
                                        type="array",
                                        items={
                                            "type": "string",
                                        },
                                    ),
                                    "accessControlAllowOriginListRegex": V1JSONSchemaProps(
                                        type="array",
                                        items={
                                            "type": "string",
                                        },
                                    ),
                                    "accessControlExposeHeaders": V1JSONSchemaProps(
                                        type="array",
                                        items={
                                            "type": "string",
                                        },
                                    ),
                                    "accessControlMaxAge": V1JSONSchemaProps(
                                        type="integer",
                                        format="int64",
                                    ),
                                    "addVaryHeader": V1JSONSchemaProps(
                                        type="boolean",
                                    ),
                                    "allowedHosts": V1JSONSchemaProps(
                                        type="array",
                                        items={
                                            "type": "string",
                                        },
                                    ),
                                    "browserXssFilter": V1JSONSchemaProps(
                                        type="boolean",
                                    ),
                                    "contentSecurityPolicy": V1JSONSchemaProps(
                                        type="string",
                                    ),
                                    "contentTypeNosniff": V1JSONSchemaProps(
                                        type="boolean",
                                    ),
                                    "customBrowserXSSValue": V1JSONSchemaProps(
                                        type="string",
                                    ),
                                    "customFrameOptionsValue": V1JSONSchemaProps(
                                        type="string",
                                    ),
                                    "customRequestHeaders": V1JSONSchemaProps(
                                        type="object",
                                        additional_properties={
                                            "type": "string",
                                        },
                                    ),
                                    "featurePolicy": V1JSONSchemaProps(
                                        description="Deprecated: use PermissionsPolicy instead.",
                                        type="string",
                                    ),
                                    "forceSTSHeader": V1JSONSchemaProps(
                                        type="boolean",
                                    ),
                                    "frameDeny": V1JSONSchemaProps(
                                        type="boolean",
                                    ),
                                    "hostsProxyHeaders": V1JSONSchemaProps(
                                        type="array",
                                        items={
                                            "type": "string",
                                        },
                                    ),
                                    "isDevelopment": V1JSONSchemaProps(
                                        type="boolean",
                                    ),
                                    "permissionsPolicy": V1JSONSchemaProps(
                                        type="string",
                                    ),
                                    "publicKey": V1JSONSchemaProps(
                                        type="string",
                                    ),
                                    "referrerPolicy": V1JSONSchemaProps(
                                        type="string",
                                    ),
                                    "sslForceHost": V1JSONSchemaProps(
                                        description="Deprecated: use RedirectRegex instead.",
                                        type="boolean",
                                    ),
                                    "sslHost": V1JSONSchemaProps(
                                        description="Deprecated: use RedirectRegex instead.",
                                        type="string",
                                    ),
                                    "sslProxyHeaders": V1JSONSchemaProps(
                                        type="object",
                                        additional_properties={
                                            "type": "string",
                                        },
                                    ),
                                    "sslRedirect": V1JSONSchemaProps(
                                        type="boolean",
                                    ),
                                    "sslTemporaryRedirect": V1JSONSchemaProps(
                                        type="boolean",
                                    ),
                                    "stsIncludeSubdomains": V1JSONSchemaProps(
                                        type="boolean",
                                    ),
                                    "stsPreload": V1JSONSchemaProps(
                                        type="boolean",
                                    ),
                                    "stsSeconds": V1JSONSchemaProps(
                                        type="integer",
                                        format="int64",
                                    ),
                                },
                            ),
                            "inFlightReq": V1JSONSchemaProps(
                                description="InFlightReq limits the number of requests being processed and served concurrently.",
                                type="object",
                                properties={
                                    "amount": V1JSONSchemaProps(
                                        type="integer",
                                        format="int64",
                                    ),
                                    "sourceCriterion": V1JSONSchemaProps(
                                        description="SourceCriterion defines what criterion is used to group requests as originating from a common source. If none are set, the default is to use the request's remote address field. All fields are mutually exclusive.",
                                        type="object",
                                        properties={
                                            "ipStrategy": V1JSONSchemaProps(
                                                description="IPStrategy holds the ip strategy configuration.",
                                                type="object",
                                                properties={
                                                    "depth": V1JSONSchemaProps(
                                                        type="integer",
                                                    ),
                                                    "excludedIPs": V1JSONSchemaProps(
                                                        type="array",
                                                        items={
                                                            "type": "string",
                                                        },
                                                    ),
                                                },
                                            ),
                                            "requestHeaderName": V1JSONSchemaProps(
                                                type="string",
                                            ),
                                            "requestHost": V1JSONSchemaProps(
                                                type="boolean",
                                            ),
                                        },
                                    ),
                                },
                            ),
                            "ipWhiteList": V1JSONSchemaProps(
                                description="IPWhiteList holds the ip white list configuration.",
                                type="object",
                                properties={
                                    "ipStrategy": V1JSONSchemaProps(
                                        description="IPStrategy holds the ip strategy configuration.",
                                        type="object",
                                        properties={
                                            "depth": V1JSONSchemaProps(
                                                type="integer",
                                            ),
                                            "excludedIPs": V1JSONSchemaProps(
                                                type="array",
                                                items={
                                                    "type": "string",
                                                },
                                            ),
                                        },
                                    ),
                                    "sourceRange": V1JSONSchemaProps(
                                        type="array",
                                        items={
                                            "type": "string",
                                        },
                                    ),
                                },
                            ),
                            "passTLSClientCert": V1JSONSchemaProps(
                                description="PassTLSClientCert holds the TLS client cert headers configuration.",
                                type="object",
                                properties={
                                    "info": V1JSONSchemaProps(
                                        description="TLSClientCertificateInfo holds the client TLS certificate info configuration.",
                                        type="object",
                                        properties={
                                            "issuer": V1JSONSchemaProps(
                                                description="TLSClientCertificateIssuerDNInfo holds the client TLS certificate distinguished name info configuration. cf https://tools.ietf.org/html/rfc3739",
                                                type="object",
                                                properties={
                                                    "commonName": V1JSONSchemaProps(
                                                        type="boolean",
                                                    ),
                                                    "country": V1JSONSchemaProps(
                                                        type="boolean",
                                                    ),
                                                    "domainComponent": V1JSONSchemaProps(
                                                        type="boolean",
                                                    ),
                                                    "organization": V1JSONSchemaProps(
                                                        type="boolean",
                                                    ),
                                                    "province": V1JSONSchemaProps(
                                                        type="boolean",
                                                    ),
                                                    "serialNumber": V1JSONSchemaProps(
                                                        type="boolean",
                                                    ),
                                                },
                                            ),
                                            "notAfter": V1JSONSchemaProps(
                                                type="boolean",
                                            ),
                                            "notBefore": V1JSONSchemaProps(
                                                type="boolean",
                                            ),
                                            "sans": V1JSONSchemaProps(
                                                type="boolean",
                                            ),
                                            "serialNumber": V1JSONSchemaProps(
                                                type="boolean",
                                            ),
                                            "subject": V1JSONSchemaProps(
                                                description="TLSClientCertificateSubjectDNInfo holds the client TLS certificate distinguished name info configuration. cf https://tools.ietf.org/html/rfc3739",
                                                type="object",
                                                properties={
                                                    "commonName": V1JSONSchemaProps(
                                                        type="boolean",
                                                    ),
                                                    "country": V1JSONSchemaProps(
                                                        type="boolean",
                                                    ),
                                                    "domainComponent": V1JSONSchemaProps(
                                                        type="boolean",
                                                    ),
                                                    "locality": V1JSONSchemaProps(
                                                        type="boolean",
                                                    ),
                                                    "organization": V1JSONSchemaProps(
                                                        type="boolean",
                                                    ),
                                                    "organizationalUnit": V1JSONSchemaProps(
                                                        type="boolean",
                                                    ),
                                                    "province": V1JSONSchemaProps(
                                                        type="boolean",
                                                    ),
                                                    "serialNumber": V1JSONSchemaProps(
                                                        type="boolean",
                                                    ),
                                                },
                                            ),
                                        },
                                    ),
                                    "pem": V1JSONSchemaProps(
                                        type="boolean",
                                    ),
                                },
                            ),
                            "plugin": V1JSONSchemaProps(
                                type="object",
                                additional_properties={"x-kubernetes-preserve-unknown-fields": True},
                            ),
                            "rateLimit": V1JSONSchemaProps(
                                description="RateLimit holds the rate limiting configuration for a given router.",
                                type="object",
                                properties={
                                    "average": V1JSONSchemaProps(
                                        type="integer",
                                        format="int64",
                                    ),
                                    "burst": V1JSONSchemaProps(
                                        type="integer",
                                        format="int64",
                                    ),
                                    "period": V1JSONSchemaProps(
                                        any_of=[
                                            V1JSONSchemaProps(
                                                type="integer",
                                            ),
                                            V1JSONSchemaProps(
                                                type="string",
                                            ),
                                        ],
                                        x_kubernetes_int_or_string=True,
                                    ),
                                    "sourceCriterion": V1JSONSchemaProps(
                                        description="SourceCriterion defines what criterion is used to group requests as originating from a common source. If none are set, the default is to use the request's remote address field. All fields are mutually exclusive.",
                                        type="object",
                                        properties={
                                            "ipStrategy": V1JSONSchemaProps(
                                                description="IPStrategy holds the ip strategy configuration.",
                                                type="object",
                                                properties={
                                                    "depth": V1JSONSchemaProps(
                                                        type="integer",
                                                    ),
                                                    "excludedIPs": V1JSONSchemaProps(
                                                        type="array",
                                                        items={
                                                            "type": "string",
                                                        },
                                                    ),
                                                },
                                            ),
                                            "requestHeaderName": V1JSONSchemaProps(
                                                type="string",
                                            ),
                                            "requestHost": V1JSONSchemaProps(
                                                type="boolean",
                                            ),
                                        },
                                    ),
                                },
                            ),
                            "redirectRegex": V1JSONSchemaProps(
                                description="RedirectRegex holds the redirection configuration.",
                                type="object",
                                properties={
                                    "permanent": V1JSONSchemaProps(
                                        type="boolean",
                                    ),
                                    "regex": V1JSONSchemaProps(
                                        type="string",
                                    ),
                                    "replacement": V1JSONSchemaProps(
                                        type="string",
                                    ),
                                },
                            ),
                            "redirectScheme": V1JSONSchemaProps(
                                description="RedirectScheme holds the scheme redirection configuration.",
                                type="object",
                                properties={
                                    "permanent": V1JSONSchemaProps(
                                        type="boolean",
                                    ),
                                    "port": V1JSONSchemaProps(
                                        type="string",
                                    ),
                                    "scheme": V1JSONSchemaProps(
                                        type="string",
                                    ),
                                },
                            ),
                            "replacePath": V1JSONSchemaProps(
                                description="ReplacePath holds the ReplacePath configuration.",
                                type="object",
                                properties={
                                    "path": V1JSONSchemaProps(
                                        type="string",
                                    ),
                                },
                            ),
                            "replacePathRegex": V1JSONSchemaProps(
                                description="ReplacePathRegex holds the ReplacePathRegex configuration.",
                                type="object",
                                properties={
                                    "regex": V1JSONSchemaProps(
                                        type="string",
                                    ),
                                    "replacement": V1JSONSchemaProps(
                                        type="string",
                                    ),
                                },
                            ),
                            "retry": V1JSONSchemaProps(
                                description="Retry holds the retry configuration.",
                                type="object",
                                properties={
                                    "attempts": V1JSONSchemaProps(
                                        type="integer",
                                    ),
                                    "initialInterval": V1JSONSchemaProps(
                                        any_of=[
                                            V1JSONSchemaProps(
                                                type="integer",
                                            ),
                                            V1JSONSchemaProps(
                                                type="string",
                                            ),
                                        ],
                                        x_kubernetes_int_or_string=True,
                                    ),
                                },
                            ),
                            "stripPrefix": V1JSONSchemaProps(
                                description="StripPrefix holds the StripPrefix configuration.",
                                type="object",
                                properties={
                                    "forceSlash": V1JSONSchemaProps(
                                        type="boolean",
                                    ),
                                    "prefixes": V1JSONSchemaProps(
                                        type="array",
                                        items={
                                            "type": "string",
                                        },
                                    ),
                                },
                            ),
                            "stripPrefixRegex": V1JSONSchemaProps(
                                description="StripPrefixRegex holds the StripPrefixRegex configuration.",
                                type="object",
                                properties={
                                    "regex": V1JSONSchemaProps(
                                        type="array",
                                        items={
                                            "type": "string",
                                        },
                                    ),
                                },
                            ),
                        },
                    ),
                },
            ),
        )
    ],
)

middlewaretcp_crd = CreateCustomResourceDefinition(
    crd_name="middlewaretcps.traefik.containo.us",
    app_name=traefik_name,
    group="traefik.containo.us",
    names=CustomResourceDefinitionNames(
        kind="MiddlewareTCP",
        list_kind="MiddlewareTCPList",
        plural="middlewaretcps",
        singular="middlewaretcp",
    ),
    annotations={
        "controller-gen.kubebuilder.io/version": "v0.6.2",
    },
    versions=[
        CustomResourceDefinitionVersion(
            name="v1alpha1",
            open_apiv3_schema=V1JSONSchemaProps(
                description="MiddlewareTCP is a specification for a MiddlewareTCP resource.",
                type="object",
                required=["metadata", "spec"],
                properties={
                    "apiVersion": V1JSONSchemaProps(
                        description="APIVersion defines the versioned schema of this representation of an object. Servers should convert recognized schemas to the latest internal value, and may reject unrecognized values. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#resources",
                        type="string",
                    ),
                    "kind": V1JSONSchemaProps(
                        description="Kind is a string value representing the REST resource this object represents. Servers may infer this from the endpoint the client submits requests to. Cannot be updated. In CamelCase. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#types-kinds",
                        type="string",
                    ),
                    "metadata": V1JSONSchemaProps(type="object"),
                    "spec": V1JSONSchemaProps(
                        description="MiddlewareTCPSpec holds the MiddlewareTCP configuration.",
                        type="object",
                        properties={
                            "inFlightConn": V1JSONSchemaProps(
                                description="TCPInFlightConn holds the TCP in flight connection configuration.",
                                type="object",
                                properties={
                                    "amount": V1JSONSchemaProps(
                                        type="integer",
                                        format="int64",
                                    ),
                                },
                            ),
                            "ipWhiteList": V1JSONSchemaProps(
                                description="TCPIPWhiteList holds the TCP ip white list configuration.",
                                type="object",
                                properties={
                                    "sourceRange": V1JSONSchemaProps(
                                        type="array",
                                        items={
                                            "type": "string",
                                        },
                                    ),
                                },
                            ),
                        },
                    ),
                },
            ),
        )
    ],
)

serverstransport_crd = CreateCustomResourceDefinition(
    crd_name="serverstransports.traefik.containo.us",
    app_name=traefik_name,
    group="traefik.containo.us",
    names=CustomResourceDefinitionNames(
        kind="ServersTransport",
        list_kind="ServersTransportList",
        plural="serverstransports",
        singular="serverstransport",
    ),
    annotations={
        "controller-gen.kubebuilder.io/version": "v0.6.2",
    },
    versions=[
        CustomResourceDefinitionVersion(
            name="v1alpha1",
            open_apiv3_schema=V1JSONSchemaProps(
                description="ServersTransport is a specification for a ServersTransport resource.",
                type="object",
                required=["metadata", "spec"],
                properties={
                    "apiVersion": V1JSONSchemaProps(
                        description="APIVersion defines the versioned schema of this representation of an object. Servers should convert recognized schemas to the latest internal value, and may reject unrecognized values. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#resources",
                        type="string",
                    ),
                    "kind": V1JSONSchemaProps(
                        description="Kind is a string value representing the REST resource this object represents. Servers may infer this from the endpoint the client submits requests to. Cannot be updated. In CamelCase. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#types-kinds",
                        type="string",
                    ),
                    "metadata": V1JSONSchemaProps(type="object"),
                    "spec": V1JSONSchemaProps(
                        description="ServersTransportSpec options to configure communication between Traefik and the servers.",
                        type="object",
                        properties={
                            "certificatesSecrets": V1JSONSchemaProps(
                                description="Certificates for mTLS.",
                                type="array",
                                items={
                                    "type": "string",
                                },
                            ),
                            "disableHTTP2": V1JSONSchemaProps(
                                description="Disable HTTP/2 for connections with backend servers.",
                                type="boolean",
                            ),
                            "forwardingTimeouts": V1JSONSchemaProps(
                                description="Timeouts for requests forwarded to the backend servers.",
                                type="object",
                                properties={
                                    "dialTimeout": V1JSONSchemaProps(
                                        description="DialTimeout is the amount of time to wait until a connection to a backend server can be established. If zero, no timeout exists.",
                                        any_of=[
                                            V1JSONSchemaProps(
                                                type="integer",
                                            ),
                                            V1JSONSchemaProps(
                                                type="string",
                                            ),
                                        ],
                                        x_kubernetes_int_or_string=True,
                                    ),
                                    "idleConnTimeout": V1JSONSchemaProps(
                                        description="IdleConnTimeout is the maximum period for which an idle HTTP keep-alive connection will remain open before closing itself.",
                                        any_of=[
                                            V1JSONSchemaProps(
                                                type="integer",
                                            ),
                                            V1JSONSchemaProps(
                                                type="string",
                                            ),
                                        ],
                                        x_kubernetes_int_or_string=True,
                                    ),
                                    "pingTimeout": V1JSONSchemaProps(
                                        any_of=[
                                            V1JSONSchemaProps(
                                                type="integer",
                                            ),
                                            V1JSONSchemaProps(
                                                type="string",
                                            ),
                                        ],
                                        x_kubernetes_int_or_string=True,
                                    ),
                                    "readIdleTimeout": V1JSONSchemaProps(
                                        any_of=[
                                            V1JSONSchemaProps(
                                                type="integer",
                                            ),
                                            V1JSONSchemaProps(
                                                type="string",
                                            ),
                                        ],
                                        x_kubernetes_int_or_string=True,
                                    ),
                                    "responseHeaderTimeout": V1JSONSchemaProps(
                                        any_of=[
                                            V1JSONSchemaProps(
                                                type="integer",
                                            ),
                                            V1JSONSchemaProps(
                                                type="string",
                                            ),
                                        ],
                                        x_kubernetes_int_or_string=True,
                                    ),
                                },
                            ),
                            "insecureSkipVerify": V1JSONSchemaProps(
                                description="Disable SSL certificate verification.",
                                type="boolean",
                            ),
                            "maxIdleConnsPerHost": V1JSONSchemaProps(
                                description="If non-zero, controls the maximum idle (keep-alive) to keep per-host. If zero, DefaultMaxIdleConnsPerHost is used.",
                                type="integer",
                            ),
                            "peerCertURI": V1JSONSchemaProps(
                                description="URI used to match against SAN URI during the peer certificate verification.",
                                type="string",
                            ),
                            "rootCAsSecrets": V1JSONSchemaProps(
                                description="Add cert file for self-signed certificate.",
                                type="array",
                                items={
                                    "type": "string",
                                },
                            ),
                            "serverName": V1JSONSchemaProps(
                                description="ServerName used to contact the server.",
                                type="string",
                            ),
                        },
                    ),
                },
            ),
        )
    ],
)

tlsoption_crd = CreateCustomResourceDefinition(
    crd_name="tlsoptions.traefik.containo.us",
    app_name=traefik_name,
    group="traefik.containo.us",
    names=CustomResourceDefinitionNames(
        kind="TLSOption",
        list_kind="TLSOptionList",
        plural="tlsoptions",
        singular="tlsoption",
    ),
    annotations={
        "controller-gen.kubebuilder.io/version": "v0.6.2",
    },
    versions=[
        CustomResourceDefinitionVersion(
            name="v1alpha1",
            open_apiv3_schema=V1JSONSchemaProps(
                description="TLSOption is a specification for a TLSOption resource.",
                type="object",
                required=["metadata", "spec"],
                properties={
                    "apiVersion": V1JSONSchemaProps(
                        description="APIVersion defines the versioned schema of this representation of an object. Servers should convert recognized schemas to the latest internal value, and may reject unrecognized values. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#resources",
                        type="string",
                    ),
                    "kind": V1JSONSchemaProps(
                        description="Kind is a string value representing the REST resource this object represents. Servers may infer this from the endpoint the client submits requests to. Cannot be updated. In CamelCase. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#types-kinds",
                        type="string",
                    ),
                    "metadata": V1JSONSchemaProps(type="object"),
                    "spec": V1JSONSchemaProps(
                        description="TLSOptionSpec configures TLS for an entry point.",
                        type="object",
                        properties={
                            "alpnProtocols": V1JSONSchemaProps(
                                type="array",
                                items={
                                    "type": "string",
                                },
                            ),
                            "cipherSuites": V1JSONSchemaProps(
                                type="array",
                                items={
                                    "type": "string",
                                },
                            ),
                            "clientAuth": V1JSONSchemaProps(
                                description="ClientAuth defines the parameters of the client authentication part of the TLS connection, if any.",
                                type="object",
                                properties={
                                    "clientAuthType": V1JSONSchemaProps(
                                        description="ClientAuthType defines the client authentication type to apply.",
                                        enum=[
                                            "NoClientCert",
                                            "RequestClientCert",
                                            "RequireAnyClientCert",
                                            "VerifyClientCertIfGiven",
                                            "RequireAndVerifyClientCert",
                                        ],
                                        type="string",
                                    ),
                                    "secretNames": V1JSONSchemaProps(
                                        description="SecretName is the name of the referenced Kubernetes Secret to specify the certificate details.",
                                        type="array",
                                        items={
                                            "type": "string",
                                        },
                                    ),
                                },
                            ),
                            "curvePreferences": V1JSONSchemaProps(
                                type="array",
                                items={
                                    "type": "string",
                                },
                            ),
                            "maxVersion": V1JSONSchemaProps(
                                type="string",
                            ),
                            "minVersion": V1JSONSchemaProps(
                                type="string",
                            ),
                            "preferServerCipherSuites": V1JSONSchemaProps(
                                type="boolean",
                            ),
                            "sniStrict": V1JSONSchemaProps(
                                type="boolean",
                            ),
                        },
                    ),
                },
            ),
        )
    ],
)

tlsstore_crd = CreateCustomResourceDefinition(
    crd_name="tlsstores.traefik.containo.us",
    app_name=traefik_name,
    group="traefik.containo.us",
    names=CustomResourceDefinitionNames(
        kind="TLSStore",
        list_kind="TLSStoreList",
        plural="tlsstores",
        singular="tlsstore",
    ),
    annotations={
        "controller-gen.kubebuilder.io/version": "v0.6.2",
    },
    versions=[
        CustomResourceDefinitionVersion(
            name="v1alpha1",
            open_apiv3_schema=V1JSONSchemaProps(
                description="TLSStore is a specification for a TLSStore resource.",
                type="object",
                required=["metadata", "spec"],
                properties={
                    "apiVersion": V1JSONSchemaProps(
                        description="APIVersion defines the versioned schema of this representation of an object. Servers should convert recognized schemas to the latest internal value, and may reject unrecognized values. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#resources",
                        type="string",
                    ),
                    "kind": V1JSONSchemaProps(
                        description="Kind is a string value representing the REST resource this object represents. Servers may infer this from the endpoint the client submits requests to. Cannot be updated. In CamelCase. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#types-kinds",
                        type="string",
                    ),
                    "metadata": V1JSONSchemaProps(type="object"),
                    "spec": V1JSONSchemaProps(
                        description="TLSStoreSpec configures a TLSStore resource.",
                        type="object",
                        properties={
                            "defaultCertificate": V1JSONSchemaProps(
                                description="DefaultCertificate holds a secret name for the TLSOption resource.",
                                required=["secretName"],
                                type="object",
                                properties={
                                    "secretName": V1JSONSchemaProps(
                                        description="SecretName is the name of the referenced Kubernetes Secret to specify the certificate details.",
                                        type="string",
                                    ),
                                },
                            )
                        },
                    ),
                },
            ),
        )
    ],
)

traefikservice_crd = CreateCustomResourceDefinition(
    crd_name="traefikservices.traefik.containo.us",
    app_name=traefik_name,
    group="traefik.containo.us",
    names=CustomResourceDefinitionNames(
        kind="TraefikService",
        list_kind="TraefikServiceList",
        plural="traefikservices",
        singular="traefikservice",
    ),
    annotations={
        "controller-gen.kubebuilder.io/version": "v0.6.2",
    },
    versions=[
        CustomResourceDefinitionVersion(
            name="v1alpha1",
            open_apiv3_schema=V1JSONSchemaProps(
                description="TraefikService is the specification for a service (that an IngressRoute refers to) that is usually not a terminal service (i.e. not a pod of servers), as opposed to a Kubernetes Service. That is to say, it usually refers to other (children) services, which themselves can be TraefikServices or Services.",
                type="object",
                required=["metadata", "spec"],
                properties={
                    "apiVersion": V1JSONSchemaProps(
                        description="APIVersion defines the versioned schema of this representation of an object. Servers should convert recognized schemas to the latest internal value, and may reject unrecognized values. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#resources",
                        type="string",
                    ),
                    "kind": V1JSONSchemaProps(
                        description="Kind is a string value representing the REST resource this object represents. Servers may infer this from the endpoint the client submits requests to. Cannot be updated. In CamelCase. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#types-kinds",
                        type="string",
                    ),
                    "metadata": V1JSONSchemaProps(type="object"),
                    "spec": V1JSONSchemaProps(
                        description="ServiceSpec defines whether a TraefikService is a load-balancer of services or a mirroring service.",
                        type="object",
                        properties={
                            "mirroring": V1JSONSchemaProps(
                                description="Mirroring defines a mirroring service, which is composed of a main load-balancer, and a list of mirrors.",
                                type="object",
                                required=["name"],
                                properties={
                                    "kind": V1JSONSchemaProps(
                                        type="string",
                                        enum=["Service", "TraefikService"],
                                    ),
                                    "maxBodySize": V1JSONSchemaProps(
                                        type="integer",
                                        format="int64",
                                    ),
                                    "mirrors": V1JSONSchemaProps(
                                        type="array",
                                        items={
                                            "description": "MirrorService defines one of the mirrors of a Mirroring service.",
                                            "type": "object",
                                            "required": ["name"],
                                            "properties": {
                                                "kind": V1JSONSchemaProps(
                                                    type="string",
                                                    enum=["Service", "TraefikService"],
                                                ),
                                                "name": V1JSONSchemaProps(
                                                    description="Name is a reference to a Kubernetes Service object (for a load-balancer of servers), or to a TraefikServic                               object (service load-balancer, mirroring, etc). The differentiation between the two is specified in the Kind field.",
                                                    type="string",
                                                ),
                                                "passHostHeader": V1JSONSchemaProps(
                                                    type="boolean",
                                                ),
                                                "percent": V1JSONSchemaProps(
                                                    type="integer",
                                                ),
                                                "port": V1JSONSchemaProps(
                                                    any_of=[
                                                        V1JSONSchemaProps(
                                                            type="integer",
                                                        ),
                                                        V1JSONSchemaProps(
                                                            type="string",
                                                        ),
                                                    ],
                                                    x_kubernetes_int_or_string=True,
                                                ),
                                                "responseForwarding": V1JSONSchemaProps(
                                                    description="ResponseForwarding holds configuration for the forward of the response.",
                                                    type="object",
                                                    properties={
                                                        "flushInterval": V1JSONSchemaProps(
                                                            type="string",
                                                        )
                                                    },
                                                ),
                                                "scheme": V1JSONSchemaProps(
                                                    type="string",
                                                ),
                                                "serversTransport": V1JSONSchemaProps(
                                                    type="string",
                                                ),
                                                "sticky": V1JSONSchemaProps(
                                                    description="Sticky holds the sticky configuration.",
                                                    type="object",
                                                    properties={
                                                        "cookie": V1JSONSchemaProps(
                                                            description="Cookie holds the sticky configuration based on cookie",
                                                            type="object",
                                                            properties={
                                                                "httpOnly": V1JSONSchemaProps(
                                                                    type="boolean",
                                                                ),
                                                                "name": V1JSONSchemaProps(
                                                                    type="string",
                                                                ),
                                                                "sameSite": V1JSONSchemaProps(
                                                                    type="string",
                                                                ),
                                                                "secure": V1JSONSchemaProps(
                                                                    type="boolean",
                                                                ),
                                                            },
                                                        )
                                                    },
                                                ),
                                                "strategy": V1JSONSchemaProps(
                                                    type="string",
                                                ),
                                                "weight": V1JSONSchemaProps(
                                                    description="Weight should only be specified when Name references a TraefikService object (and to be precise, one that embeds a Weighted Round Robin).",
                                                    type="integer",
                                                ),
                                            },
                                        },
                                    ),
                                    "name": V1JSONSchemaProps(
                                        description="Name is a reference to a Kubernetes Service object (for a load-balancer of servers), or to a TraefikService object (service load-balancer, mirroring, etc). The differentiation between the two is specified in the Kind field.",
                                        type="string",
                                    ),
                                    "namespace": V1JSONSchemaProps(
                                        type="string",
                                    ),
                                    "passHostHeader": V1JSONSchemaProps(
                                        type="boolean",
                                    ),
                                    "port": V1JSONSchemaProps(
                                        any_of=[
                                            V1JSONSchemaProps(
                                                type="integer",
                                            ),
                                            V1JSONSchemaProps(
                                                type="string",
                                            ),
                                        ],
                                        x_kubernetes_int_or_string=True,
                                    ),
                                    "responseForwarding": V1JSONSchemaProps(
                                        description="ResponseForwarding holds configuration for the forward of the response.",
                                        type="object",
                                        properties={
                                            "flushInterval": V1JSONSchemaProps(
                                                type="string",
                                            )
                                        },
                                    ),
                                    "scheme": V1JSONSchemaProps(
                                        type="string",
                                    ),
                                    "serversTransport": V1JSONSchemaProps(
                                        type="string",
                                    ),
                                    "sticky": V1JSONSchemaProps(
                                        description="Sticky holds the sticky configuration.",
                                        type="object",
                                        properties={
                                            "cookie": V1JSONSchemaProps(
                                                description="Cookie holds the sticky configuration based on cookie",
                                                type="object",
                                                properties={
                                                    "httpOnly": V1JSONSchemaProps(
                                                        type="boolean",
                                                    ),
                                                    "name": V1JSONSchemaProps(
                                                        type="string",
                                                    ),
                                                    "sameSite": V1JSONSchemaProps(
                                                        type="string",
                                                    ),
                                                    "secure": V1JSONSchemaProps(
                                                        type="boolean",
                                                    ),
                                                },
                                            )
                                        },
                                    ),
                                    "strategy": V1JSONSchemaProps(
                                        type="string",
                                    ),
                                    "weight": V1JSONSchemaProps(
                                        description="Weight should only be specified when Name references a TraefikService object (and to be precise, one that embeds a Weighted Round Robin).",
                                        type="integer",
                                    ),
                                },
                            ),
                            "weighted": V1JSONSchemaProps(
                                description="WeightedRoundRobin defines a load-balancer of services.",
                                type="object",
                                properties={
                                    "services": V1JSONSchemaProps(
                                        type="array",
                                        items={
                                            "description": "Service defines an upstream to proxy traffic.",
                                            "type": "object",
                                            "required": ["name"],
                                            "properties": {
                                                "kind": V1JSONSchemaProps(
                                                    type="string",
                                                    enum=["Service", "TraefikService"],
                                                ),
                                                "name": V1JSONSchemaProps(
                                                    description="Name is a reference to a Kubernetes Service object (for a load-balancer of servers), or to a TraefikServic                               object (service load-balancer, mirroring, etc). The differentiation between the two is specified in the Kind field.",
                                                    type="string",
                                                ),
                                                "passHostHeader": V1JSONSchemaProps(
                                                    type="boolean",
                                                ),
                                                "port": V1JSONSchemaProps(
                                                    any_of=[
                                                        V1JSONSchemaProps(
                                                            type="integer",
                                                        ),
                                                        V1JSONSchemaProps(
                                                            type="string",
                                                        ),
                                                    ],
                                                    x_kubernetes_int_or_string=True,
                                                ),
                                                "responseForwarding": V1JSONSchemaProps(
                                                    description="ResponseForwarding holds configuration for the forward of the response.",
                                                    type="object",
                                                    properties={
                                                        "flushInterval": V1JSONSchemaProps(
                                                            type="string",
                                                        )
                                                    },
                                                ),
                                                "scheme": V1JSONSchemaProps(
                                                    type="string",
                                                ),
                                                "serversTransport": V1JSONSchemaProps(
                                                    type="string",
                                                ),
                                                "sticky": V1JSONSchemaProps(
                                                    description="Sticky holds the sticky configuration.",
                                                    type="object",
                                                    properties={
                                                        "cookie": V1JSONSchemaProps(
                                                            description="Cookie holds the sticky configuration based on cookie",
                                                            type="object",
                                                            properties={
                                                                "httpOnly": V1JSONSchemaProps(
                                                                    type="boolean",
                                                                ),
                                                                "name": V1JSONSchemaProps(
                                                                    type="string",
                                                                ),
                                                                "sameSite": V1JSONSchemaProps(
                                                                    type="string",
                                                                ),
                                                                "secure": V1JSONSchemaProps(
                                                                    type="boolean",
                                                                ),
                                                            },
                                                        )
                                                    },
                                                ),
                                                "strategy": V1JSONSchemaProps(
                                                    type="string",
                                                ),
                                                "weight": V1JSONSchemaProps(
                                                    description="Weight should only be specified when Name references a TraefikService object (and to be precise, one that embeds a Weighted Round Robin).",
                                                    type="integer",
                                                ),
                                            },
                                        },
                                    ),
                                    "sticky": V1JSONSchemaProps(
                                        description="Sticky holds the sticky configuration.",
                                        type="object",
                                        properties={
                                            "cookie": V1JSONSchemaProps(
                                                description="Cookie holds the sticky configuration based on cookie",
                                                type="object",
                                                properties={
                                                    "httpOnly": V1JSONSchemaProps(
                                                        type="boolean",
                                                    ),
                                                    "name": V1JSONSchemaProps(
                                                        type="string",
                                                    ),
                                                    "sameSite": V1JSONSchemaProps(
                                                        type="string",
                                                    ),
                                                    "secure": V1JSONSchemaProps(
                                                        type="boolean",
                                                    ),
                                                },
                                            )
                                        },
                                    ),
                                },
                            ),
                        },
                    ),
                },
            ),
        )
    ],
)
