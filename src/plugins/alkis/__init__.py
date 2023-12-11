import os
from plugins.alkis.controllers import ALKISController

__alkis_controller = None


name = "ALKIS"

def load_plugin(app, handler):

    global __alkis_controller
    __alkis_controller = ALKISController(app, handler)

