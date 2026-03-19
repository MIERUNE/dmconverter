# プラグインのエントリーポイント


def classFactory(iface):
    from .core.dmconverter.plugin import Plugin

    return Plugin(iface)
