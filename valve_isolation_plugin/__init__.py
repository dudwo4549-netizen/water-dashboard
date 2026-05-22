def classFactory(iface):
    from .valve_isolation_plugin import ValveIsolationPlugin
    return ValveIsolationPlugin(iface)
