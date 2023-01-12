# K8s Resources

## Kubeconfig

Access to K8s clusters is configured using a Kubeconfig. This configuration can be stored in a file or as an object.
A Kubeconfig therefore stores information about clusters, users, namespaces, and authentication mechanisms which let us access our K8s Clusters.

When we use K8s locally on our machine, our kubeconfig file is usually stored at ~/.kube/config
A file that is used to configure access to a cluster is called a kubeconfig file. This is a generic way of referring to kubernetes configuration files. It does not mean that there is a file named kubeconfig. To view your local kubeconfig using `kubectl config view`

### Kubeconfig Precedence

If you’re using kubectl, here’s the preference that takes effect while determining which kubeconfig file is used.

1. use --kubeconfig flag, if specified
2. use KUBECONFIG environment variable, if specified
3. use ~/.kube/config file

This precedence is mentioned [here](https://kubernetes.io/docs/reference/generated/kubectl/kubectl-commands#config) and it is [codified](https://github.com/kubernetes/client-go/blob/e478dd3a68a8ebf260beb7b9522bcc87cf4c971f/tools/clientcmd/loader.go#L137) here.

Links:

- [Official Docs](https://kubernetes.io/docs/tasks/access-application-cluster/configure-access-multiple-clusters/)
- [Go Doc]: https://godoc.org/k8s.io/client-go/tools/clientcmd/api#Config
- [Mastering Kubeconfig](https://ahmet.im/blog/mastering-kubeconfig/)
- [Authenticating GKE without gcloud](https://ahmet.im/blog/authenticating-to-gke-without-gcloud/)
