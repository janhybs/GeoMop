from LayerEditor.leconfig import cfg
from LayerEditor.leconfig.leconfig import _Config as Config

def set_empty_config():
    Config.SERIAL_FILE = "LayerEditorData_test"
    cfg.config = Config()

def clean_config():
    import gm_base.config
    gm_base.config.delete_config_file("LayerEditorData_test")
