import textwrap

class Tracker:
    example = textwrap.dedent("""
    # REQUIRES CODE IN TWO DIFFERENT NOTEBOOK CELLS

    The way this works is to start one notebook cell
    with the tracker code.  This will remain live
    and will get updated whenever you run the logging cell.

    After the tracking cell has been set up, you can
    run the logging cell multiple times and the
    tracking cell's visualization will be updated.

    # -- Single-trace use case -----------------------

    # In tracking notebook cell
    tracker = Tracker(logy=True)
    tracker.init()

    # In logging cell

    for nn in np.linspace(1, 20, 50):
        x = np.linspace(.1, nn, 500)
        y = 1 / x
        tracker.update(x, y)
        time.sleep(.02)



    # -- Multi-trace use case -----------------------
    # In tracking notebook cell
    ylim = (-2, 2)
    tracker1 = Tracker(label='+s', ylim=ylim)
    tracker2 = Tracker(label='-s', ylim=ylim)
    tracker3 = Tracker(label='+c', ylim=ylim)
    tracker4 = Tracker(label='-c', ylim=ylim)

    hv.Overlay([
        tracker1.init(),
        tracker2.init(),
        tracker3.init(),
        tracker4.init()
    ]).collate()

    # In logging cell
    for nn in np.linspace(0, 20, 50):
        x = np.linspace(0, nn, 500)
        y = np.sin(2 * np.pi * x / (4))
        y2 = np.cos(2 * np.pi * x / (4))
        tracker1.update(x, y)
        tracker2.update(x, -y)
        tracker3.update(x, y2)
        tracker4.update(x, -y2)
        time.sleep(.01)
    """)

    def __init__(
            self,
            label='metric', ylim=None,  logy=False,  width=800, height=400):
        from holoviews.streams import Pipe
        import holoviews as hv
        self.label = label
        self.ylim = ylim

        self.logy = logy
        self.pipe = Pipe(data=None)
        if hv.Store.current_backend == 'bokeh':
            self.dmap = hv.DynamicMap(
                self._plotter, streams=[self.pipe]
            ).opts(framewise=True, width=width, height=height, logy=self.logy)
        else:
            self.dmap = hv.DynamicMap(
                self._plotter, streams=[self.pipe]
            ).opts(framewise=True, fig_inches=12, aspect=2, logy=self.logy)

    def _plotter(self, data):
        import holoviews as hv
        default_val = hv.Curve(([], []))
        if data is None:
            return default_val
        (x, y) = data

        c = hv.Curve((x, y), label=self.label)
        return c

    def init(self):
        return self.dmap

    def update(self, x, y):
        self.pipe.send((x, y))

