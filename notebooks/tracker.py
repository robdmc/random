class Tracker:
    def __init__(self, logy=False,  width=800, height=400):
        from holoviews.streams import Pipe
        import holoviews as hv

        self.logy = logy
        self.pipe = Pipe(data=None)
        if hv.Store.current_backend == 'bokeh':
            self.dmap = hv.DynamicMap(self._plotter, streams=[self.pipe]).opts(framewise=True, width=width, height=height, logy=self.logy)
        else:
            self.dmap = hv.DynamicMap(self._plotter, streams=[self.pipe]).opts(framewise=True, logy=self.logy, fig_inches=12, aspect=2)

    def _plotter(self, data):
        import holoviews as hv
        default_val = hv.Curve(([], []))
        if data is None:
            return default_val
        (x, y) = data

        return hv.Curve((x, y))

    def init(self):
        return self.dmap

    def update(self, x, y):
        self.pipe.send((x, y))
