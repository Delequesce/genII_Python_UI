class BlitManager:
    def __init__(self, canvas, animated_artists=()):
        """
        Parameters
        -----------
        canvas : FigureCanvasAgg
            The canvas to work with, this only works for the subclassed of the Agg canvas
            which have the `FigureCanvasAgg.copy_from_bbox` and 
            `FigureCanvasAgg.restore_region` methods

        animated_artists : Iterable[Artist]
            List of artists to manage
        """
        self.canvas = canvas
        self._bg = None
        self._artists = []

        for a in animated_artists:
            self.add_artists(a)
        # grab the background on every draw 
        self.cid = canvas.mpl_connect("draw_event", self.on_draw)

    def on_draw(self, event):
        """Callback to register with 'draw_event'."""
        cv = self.canvas
        if event is not None:
            if event.canvas != cv:
                raise RuntimeError
        self._bg = cv.copy_from_bbox(cv.figure.bbox)
        self._draw_animated()

    def add_artist(self, art):
        """
        Add an artist to be managed.

        Parameters
        ----------
        art: Artist

            The artist to be added. Will be set to 'animated'. *art* must be in the
            figure associated with this canvas this class is managing.
        """
        if art.figure != self.canvas.figure:
            raise RuntimeError
        
        art.set_animated(True)
        self._artists.append(art)

    def _draw_animated(self):
        """Draw all of the animated artists"""
        fig = self.canvas.figure
        for a in self._artists:
            fig.draw_artist(a)
    
    def update(self):
        """Update the screen with animated artists"""
        cv = self.canvas
        fig = cv.figure
        if self._bg is None:
            self.on_draw(None)
        else:
            # restore background
            cv.restore_region(self._bg)
            # draw all of the animated artists
            self._draw_animated()
            # Update GUI State
            cv.blit(fig.bbox)
        # let the GUI event loop process anything it has to do
        cv.flush_events()
        

