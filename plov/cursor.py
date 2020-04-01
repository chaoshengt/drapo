""" Extensions to Matplotlib: Cursor class, and ginput/hinput functions.

This module contains a Cursor class (cursor that moves with the mouse) and
ginput/hinput functions similar to the matplotlib ginput, but with a cursor
and allowing zooming/panning in the case of hinput.
"""

# TODO - To allow cursor to appear on multiple figures, it is necessary to
# connect figure events to callbacks for every existing figure --> do a figure list
# and connect one by one.


import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import time

from .interactive_object import InteractiveObject

# ================================= example ==================================


def main():
    
    matplotlib.use('Qt5Agg')  # blitting does not work well with tkagg ot macosx
    
    """ Example of use."""
    x = [0, 1, 2, 3, 4]
    y = [4, 7, 11, 18, 33]

    z = np.random.randn(1000)

    fig, (ax1, ax2) = plt.subplots(1, 2)
    ax1.plot(x, y, '-ob')
    ax2.plot(z, '-ok')

    # without the block=False option, the program does not go to hinput
    plt.show(block=False)

    hinput(4)

   
# =============================== Cursor class ===============================


class Cursor(InteractiveObject):
    """Cursor following the mouse on any axes of a matplotlib figure.

    This class creates a cursor that moves along with the mouse. It is drawn
    only within existing axes, but contrary to the matplotlib widget Cursor,
    is not bound to specific axes: moving the mouse over different axes will
    plot the cursor in these other axes. Right now, the cursor is bound to a
    certain figure, however this could be changed easily.

    Cursor style can be modified with the options `color`, `linestyle` and 
    `linewidth`, which correspond to matplotlib's parameters of the same name.
    By default, color is red, linestyle is dotted (:), linewidth is 1.

    Cursor apparance can also be changed by specific key strokes:
        - space bar to toggle visibility (on/off)
        - up/down arrows: increase or decrease width (linewidth)
        - left/right arrows: cycle through different cursor colors

    The cursor can also leave marks and/or record click positions if there is
    a click with a specific button (by default, left mouse button). Clicks can
    be removed with the remove button (by default, right mouse button), and
    stopped with the stop button (by default, middle mouse button).

    Addition / removal / stop of clicks are also achieved by key strokes:
        - 'a' for addition (corresponds to left click)
        - 'z' for removal (corresponds to right click)
        - 'enter' for stopping clicks (corresponds to middle click)

    Parameters
    ----------
    All parameters optional so that a cursor can be created by `Cursor()`.

    - `fig` (matplotlib figure, default: current figure, specified as None).
    - `color` (matplotlib's color, default: red, i.e. 'r').
    - `linestyle` (matplotlib's linestyle, default: dotted ':').
    - `linewidth` (float, default: 1.0). Line width.
    - `blit` (bool, default: True). Blitting for performance.
    - `show_clicks` (bool, default:False). Mark location of clicks.
    - `record_clicks` (bool, default False). Create a list of click positions.

    The 3 following parameters can be 1, 2, 3 (left, middle, right mouse btns).
    - `mouse_add` (int, default 1). Adds a (x, y) point by clicking.
    - `mouse_pop` (int, default 3). Removes most recently added point.
    - `mouse_stop`(int, default 2). Stops click recording. Same as reaching n.

    The 3 following parameters are useful for ginput-like functions.
    - `n` (int, default 1000). Cursor deactivates after n clicks.
    - `block` (bool, default False). Block console until nclicks is reached.
    - `timeout` (float, default 0, i.e. infinite) timeout for blocking.

    The last 2 parameters customize appearance of click marks when shown.
    - `mark_symbol` (matplolib's symbol, default: '+')
    - `mark_size` (matplotlib's markersize, default: 10)


    Useful class methods
    --------------------

    - `erase_marks()`: erase click marks on the plot.
    - `erase_data()`: reset recorded click data.

    The methods `create` and `delete` are used internally within the class and
    are not meant for the user.

    Useful class attributes
    -----------------------

    - `fig`: matplotlib figure the cursor is active in. Fixed.
    - `ax`: matplotlib axes the cursor is active in. Changes in subplots.
    - `visible`: bool, sets whether cursor drawn or not when in axes.
    - `inaxes`: book, true when mouse (and thus cursor) is in axes
    - `clicknumber`: track the number of recorded clicks.
    - `clickdata`: stores the (x, y) data of clicks in a list.
    - `marks`: list of matplotlib artists containing all click marks drawn.

    Notes
    -----

    - By default, the cursor is created on the active figure/axes. 
    To instanciate a cursor in other figure/axes, either specify the key/ax
    parameters, or use `ClickFig()` to activate these axes.
    
    - As in matplotlib's ginput, `mouse_add`, `mouse_pop` and `mouse_stop`
    have keystroke equivalents, respectively `a`, `z` and `enter`. Only the
    last one is the same as matplotlib's ginput, to avoid interactions with
    other matplotlib's interactive features (e.g. backspace for "back").

    - Currently, the mark color is always the same as the cursor.

    - It is not allowed to have more than 1 cursor per figure, to avoid
    conflics between cursors in blitting mode.

    - Using panning and zooming works with the cursor on; to enable this,
    blitting is temporarily suspended during a click+drag event.

    - As a result, the cursor does not reappear immediately after panning or
    zooming if blitting is activated, but one needs to move the mouse.

    """
    
    name = 'Cursor'
    
    
    def __init__(self, fig=None, color='r', linestyle=':', linewidth=1, 
                 blit=True, show_clicks=False, record_clicks=False,
                 mouse_add=1, mouse_pop=3, mouse_stop=2,
                 n=1000, block=False, timeout=0,
                 mark_symbol='+', mark_size=10):
        """Note: cursor drawn only when the mouse enters axes."""
        
        super().__init__(fig, color=color, blit=blit, block=block)    

        # Cursor state attributes
        self.press = False  # active when mouse is currently pressed
        self.visible = True  # can be True even if cursor not drawn (e.g. because mouse is outside of axes)
        self.inaxes = False  # True when mouse is in axes

        # Appearance options
        self.style = linestyle
        self.width = linewidth
        self.marksymbol = mark_symbol
        self.marksize = mark_size
        
        # Recording click options
        self.markclicks = show_clicks
        self.recordclicks = record_clicks
        self.clickbutton = mouse_add
        self.removebutton = mouse_pop
        self.stopbutton = mouse_stop

        # Recording click data
        self.clicknumber = 0  # tracks the number of clicks
        self.n = n  # maximum number of clicks, after which cursor is deactivated
        self.clickdata = []  # stores the (x, y) data of clicks in a list
        self.marks = []  # list containing all artists drawn
        
        self.fig.canvas.draw()

        # the blocking option below needs to be after connect()
        if self.block:
            self.fig.canvas.start_event_loop(timeout=timeout)
            

    def __repr__(self):

        name = self.__class__.name
        base_message = f'{name} on Fig. {self.fig.number}.'

        if self.clickbutton == 1:
            button = "left"
        elif self.clickbutton == 2:
            button = 'middle'
        elif self.clickbutton == 3:
            button = 'right'
        else:
            button = 'unknown'

        if self.markclicks:
            add_message = f"Leaves '{self.marksymbol}' marks when {button} mouse button is pressed. "
        else:
            add_message = ''

        if self.recordclicks:
            add_message += f'Positions of clicks with the {button} button is recorded in the clickdata attribute.'
        else:
            add_message += f'Positions of clicks not recorded.'

        return base_message + ' ' + add_message



# =========================== main cursor methods ============================


    def create(self, event):
        """Draw a cursor (h+v lines) that stop at the edge of the axes."""
        ax = self.ax
        xmin, xmax = ax.get_xlim()
        ymin, ymax = ax.get_ylim()
        
        self.delete_others('fig') # delete all other existing cursors on the figure

        x, y = event.xdata, event.ydata
        # horizontal and vertical cursor lines, the animated option is for blitting
        hline, = ax.plot([xmin, xmax], [y, y], color=self.color,
                         linewidth=self.width, linestyle=self.style,
                         animated=self.__class__.blit)
        vline, = ax.plot([x, x], [ymin, ymax], color=self.color,
                         linewidth=self.width, linestyle=self.style,
                         animated=self.__class__.blit)

        # because plotting the lines can change the initial xlim, ylim
        ax.set_xlim(xmin, xmax)
        ax.set_ylim(ymin, ymax)
        
        self.all_artists = hline, vline
        # Note: addition to all_objects is made automatically by InteractiveObject parent class
        self.__class__.moving_objects.add(self)


    def update_position(self, position):
        """Update position of the cursor to follow mouse event."""

        x, y = position  
        ax = self.ax
        
        hline, vline = self.all_artists
    
        # accommodates changes in axes limits while cursor is on
        xmin, xmax = ax.get_xlim()
        ymin, ymax = ax.get_ylim()
      
        hline.set_xdata([xmin, xmax])
        hline.set_ydata([y, y])
        vline.set_xdata([x, x])
        vline.set_ydata([ymin, ymax])
        
        
    def set_press_info(self, event):
        press_info = {'currently_pressed': True, 
                      'click_position': (event.xdata, event.ydata)}
        return press_info


    def erase_marks(self):
        """Erase plotted clicks (marks) without removing click data"""
        for mark in self.marks:
            mark.remove()
        self.fig.canvas.draw()
        

    def erase_data(self):
        """Erase data of recorded clicks"""
        self.clickdata = []
        
    
    def add_point(self, pos):
        """Add point to the click data (triggered by click or key press)"""
        x, y = pos
        if self.recordclicks:
            self.clickdata.append((x, y))
            self.clicknumber += 1

        if self.markclicks:
            mark, = self.ax.plot(x, y, marker=self.marksymbol, color=self.color,
                                 markersize=self.marksize)
            self.marks.append(mark)


    def remove_point(self):
        """Add point to the click data (triggered by click or key press)"""            
        if self.recordclicks:
            if self.clicknumber == 0:
                pass
            else:
                self.clicknumber -= 1
                self.clickdata.pop(-1)  # remove last element

        if self.markclicks:
            if len(self.marks) == 0:
                pass
            else:
                mark = self.marks.pop(-1)
                mark.remove()


# ============================ callback functions ============================


    def on_enter_axes(self, event):
        """Create a cursor when mouse enters axes."""
        self.inaxes = True
        self.ax = event.inaxes
        if self.visible:
            self.create(event)    
        if self.__class__.blit:
            self.__class__.background = self.fig.canvas.copy_from_bbox(self.ax.bbox)
            

    def on_leave_axes(self, event):
        """Erase cursor when mouse leaves axes."""
        self.inaxes = False
        if self.visible and not self.press_info['currently_pressed']:
            self.erase()
            

    def on_motion(self, event):
        """Update position of the cursor when mouse is in motion."""
        # nothing if pressed to avoid weird interactions with panning
        if self.visible and self.inaxes and not self.press_info['currently_pressed']:
            self.update_graph(event)
        

    def on_mouse_press(self, event):
        """If mouse is pressed, deactivate cursor temporarily."""
        self.press_info = self.set_press_info(event)
        if self.visible and self.inaxes:
             self.erase()
        
        
    def on_mouse_release(self, event):
        """When releasing click, reactivate cursor and redraw figure.

        This is in order to accommodate potential zooming/panning.
        """
        
        self.press_info['currently_pressed'] = False
        if self.visible and self.inaxes:
            self.create(event)
            
        # I don't understand why I need to do the hack below to not have a
        # strange re-appearance of the background before zooming (panning is ok)
        # when the mouse go into motion again (not rightaway). Even more
        # surprising is that if I shortcut on_motion by calling update_graph
        # directly here, it does not work.
        self.__class__.initiating_motion = True  # to reactivate cursor


        # See if click needs to be recorded.        

        x, y = (event.xdata, event.ydata)
        # line below avoids recording clicks during panning/zooming
        if (x, y) == self.press_info['click_position']:

            if event.button == self.clickbutton:
                self.add_point((x, y))

            elif event.button == self.removebutton:
                self.remove_point()

        if self.clicknumber == self.n or event.button == self.stopbutton:
            print('Cursor disconnected (max number of clicks, or stop button pressed).')
            self.delete()
            
        
                

    def on_key_press(self, event):
        """Key press controls. Space bar toggles cursor visibility.

        All controls:
            - space bar: toggles cursor visibility
            - up/down arrows: increase or decrease cursor size
            - left/right arrows: cycles through colors
            - "a" : add point
            - "z" : cancel last point
            - enter : stop recording
        """
# ----------------- changes in appearance of cursor --------------------------

        commands_color = ['shift+right', 'shift+left']  # keys to change color
        commands_width = ['shift+up', 'shift+down']

        if event.key == " ":  # Space Bar     
            if self.inaxes: # create or delete cursor only if it's in axes
                self.erase() if self.visible else self.create(event)
            self.visible = not self.visible  # always change visibility status
            
        if event.key == commands_width[0]:
            self.width += 0.5

        if event.key == commands_width[1]:
            self.width = self.width-0.5 if self.width > 0.5 else 0.5

        if event.key in commands_color:
            # finds at which position the current color is in the list
            colorindex = self.__class__.colors.index(self.color)
            if event.key == commands_color[1]:
                colorindex -= 1
            else:
                colorindex += 1
            colorindex = colorindex % len(self.__class__.colors)
            self.color = self.__class__.colors[colorindex]

        if event.key in commands_color + commands_width:
            self.erase()  # easy way to not have to update artist
            self.create(event)

# ------------------- recording or removing click data -----------------------

        x, y = (event.xdata, event.ydata)

        if event.key == 'a':
            self.add_point((x, y))
            
        # I use 'z' here because backspace (as used in ginput) interferes
        # with the interactive "back" option in matplotlib
        elif event.key == 'z':
            self.remove_point()
            
# --------------------implement changes on graph -----------------------------
        
        # hack to see changes directly and to prevent display bugs
        self.__class__.initiating_motion = True
        self.update_graph(event)
          
# ------------------------ stop if necessary ---------------------------------

        if self.clicknumber == self.n or event.key == 'enter':
            print('Cursor disconnected (max number of clicks, or stop button pressed).')
            self.delete()



    def on_close(self, event):
        """Delete cursor if figure is closed"""
        self.delete()


# ========================== ginput-like functions ==========================


def ginput(*args, **kwargs):
    """Identical to matplotlib's ginput, with added cursor for easier clicking.

    Use of hinput is preferred, because it allows for zooming/panning.

    Key shortcuts and mouse clicks follow matplotlib's behavior. The Cursor
    class only acts on the cursor here (appearance, with key Cursor class
    associated key shortcuts), not on the clicking and data recording which
    follow matplotlib ginput. See matplotlib.pyplot.ginput for help.
    """
    c = Cursor(record_clicks=False, show_clicks=False, block=False)
    data = plt.ginput(*args, **kwargs)
    del c
    return data


def hinput(n=1, timeout=0, show_clicks=True,
           mouse_add=1, mouse_pop=3, mouse_stop=2,
           blit=True):
    """Similar to ginput, but zooming/panning does not add extra click data.

    Here, contrary to ginput, key shortcuts and mouse clicks follow the
    plov Cursor class behavior, in particular the key shortcuts are
    `a`, `z`, `enter` instead of any key, backspace and enter. See
    Cursor class documentation for more info. All Cursor class interactive
    features are usable.

    Parameters
    ----------

    Parameters are exactly the same as matplotlib.pyplot.ginput, with only an
    additional one: blit (bool, default True): blitting for performance.

    Returns
    -------

    List of tuples corresponding to the list of clicked (x, y) coordinates.

    """
    c = Cursor(block=True, record_clicks=True, show_clicks=show_clicks, n=n,
               mouse_add=mouse_add, mouse_stop=mouse_stop, mouse_pop=mouse_pop,
               blit=blit)
    data = c.clickdata
    time.sleep(0.2)  # just to have time to see the last click and its mark
    c.erase_marks()
    return data


# ================================ direct run ================================

if __name__ == '__main__':
    main()
