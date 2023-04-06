c = get_config()  # type: ignore

## Answer yes to any prompts.
#  Default: False
c.JupyterApp.answer_yes = True

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
