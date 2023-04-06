c = get_config()  # type: ignore

## Answer yes to any prompts.
#  Default: False
c.JupyterApp.answer_yes = True

## Set the Access-Control-Allow-Origin header
#
#          Use '*' to allow any origin to access your server.
#
#          Takes precedence over allow_origin_pat.
#  Default: ''
c.ServerApp.allow_origin = "*"

## Allow requests where the Host header doesn't point to a local server
#
#         By default, requests get a 403 forbidden response if the 'Host' header
#         shows that the browser thinks it's on a non-local domain.
#         Setting this option to True disables this check.
#
#         This protects against 'DNS rebinding' attacks, where a remote web server
#         serves you a page and then changes its DNS to send later requests to a
#         local IP, bypassing same-origin checks.
#
#         Local IP addresses (such as 127.0.0.1 and ::1) are allowed as local,
#         along with hostnames configured in local_hostnames.
#  Default: False
c.ServerApp.allow_remote_access = True

## The IP address the Jupyter server will listen on.
#  Default: 'localhost'
c.ServerApp.ip = "0.0.0.0"

## Whether to allow the user to run the server as root.
#  Default: False
c.ServerApp.allow_root = True

## Hashed password to use for web authentication.
#
#                        To generate, type in a python/IPython shell:
#
#                          from jupyter_server.auth import passwd; passwd()
#
#                        The string should be of the form type:salt:hashed-password.
#  Default: 'admin'
c.ServerApp.password = "argon2:$argon2id$v=19$m=10240,t=10,p=8$cRdZ7rDVwLUIXwsUPPDing$cqcROe+Zj9l+1AfMS7hbp4T0iMUWDkJLo8AJDeEFFlQ"

## Supply overrides for terminado. Currently only supports "shell_command".
#  Default: {}
c.ServerApp.terminado_settings = {"shell_command": ["/usr/bin/zsh"]}

## Whether to enable collaborative mode (experimental).
#  Default: False
c.LabApp.collaborative = True

## The directory for workspaces
c.LabApp.workspaces_dir = "/mnt/.jupyter/lab/workspaces"
