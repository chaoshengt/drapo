"""InteractiveObject class, for plot-ov. Not for direct use, just subclassing.

Classes Line, Rect and Cursor subclass InteractiveObject defined here.
"""

import matplotlib.pyplot as plt
from matplotlib.colors import is_color_like


def main():
    obj = InteractiveObject()  # For testing purposes
    return obj


class InteractiveObject:
    """Base class for moving objects on a figure. Used for subclassing only.
    
    See CONTRIBUTING.md for information on how to use this class.
    """
    
    name = 'Interactive Object'
    
    all_interactive_objects = []  # tracking all instances of all subclasses
    # (use the all_instances() method to get instances of a single class)
    # This list is returned by the classmethod all_objects().
    
    moving_objects = set()  # objects currently moving on figure. Includes
    # all subclasses, to be able to manage motion of objects of different 
    # classes on the same figure.
    
    leader = None  # Leader object that synchronizes motion and drawing of all
    # objects when several objects are selected/moving at the same time.
    # This feature is required due to blitting rendering issues.
    
    initiating_motion = False  # True when the leading object had been selected
    
    # Attributes for fast rendering of motion with blitting.
    blit = True
    background = None
    
    # Define default colors of the class (potentially cycled through by some
    # methods. If user specifies a color not in the list, it is added to the
    # class colors.
    white = '#eeeeee' # not completely white so that it is still visible
    black = '#111111' # same in case of black background
    colors = [black, 'r', 'b', 'g', white]
    

    def __init__(self, fig=None, ax=None, color=None, blit=True, block=False):     

        self.fig = plt.gcf() if fig is None else fig
        self.ax = plt.gca() if ax is None else ax

        # This is because adding lines can re-dimension axes limits
        self.xlim = self.ax.get_xlim()
        self.ylim = self.ax.get_ylim()
        
        # Connect matplotlib event handling to callback functions
        self.connect()
        
        # Tracks instances of any interactive objects of any subclass.
        self.all_interactive_objects.append(self)
                
        self.all_artists = [] # all artists the object is made of
        self.all_pts = []  # all individual tracking points the object is made of
        
        # set that stores info about what artists are picked
        self.picked_artists = set() # they can be different frmo the active
        # artists, because e.g. when a line moves as a whole, only the line
        # is picked, but the two edge points need to be moving/active as well.
        
        self.moving = False  # faster way to check moving objects than to measure the length of moving_objects
        self.press_info = {'currently_pressed': False}  # stores useful useful mouse click information

        # the last object to be instanciated dictates if blitting is true or not
        self.__class__.blit = blit
        # Reset leading artist when instanciating a new object
        self.__class__.leader = None
        
        # defines whether the interactive object is blocking the console or not
        self.block = block
        
        if color is None:
            self.color = self.__class__.colors[0]
        elif not is_color_like(color):
            print('Warning: color not recognized. Falling back to default.')
            self.color = self.__class__.colors[0]
        else:
            self.color = color
            if color not in self.__class__.colors:
                self.__class__.colors.append(color)
                
        # Transforms functions to go from px to data coords.
        # Need to be redefined if figure is resized
        self.datatopx = self.ax.transData.transform  # transform between data coords to px coords.
        self.pxtodata = self.ax.transData.inverted().transform  # pixels to data coordinates     
        

        # this seems to be a generic way to bring window to the front but I
        # have not checked with all backends etc, and it does not always work
        plt.get_current_fig_manager().show()


    def __repr__(self):
        object_list = self.__class__.class_objects()
        objects_on_fig = [obj for obj in object_list if obj.fig == self.fig]
        n_on_fig = len(objects_on_fig)
        n = objects_on_fig.index(self) + 1
        name = self.__class__.name
        return f'{name} #{n}/{n_on_fig} in Fig. {self.fig.number}.'

    def __str__(self):
        #name = self.__class__.name
        #return f'{name} on Fig. {self.fig.number}.'
        return self.__repr__()
    
# ================================== methods =================================
    
    def update_graph(self, event):
        """Update graph with the moving artists. Called only by the leader."""
        
        canvas = self.fig.canvas
        ax = self.ax

        if self.__class__.blit and self.__class__.initiating_motion:
            canvas.draw()
            self.__class__.background = canvas.copy_from_bbox(ax.bbox)
            self.__class__.initiating_motion = False

        if self.__class__.blit:
            # without this line, the graph keeps all successive positions of
            # the cursor on the screen
            canvas.restore_region(self.__class__.background)

        # now the leader triggers update of all moving artists including itself
        for obj in self.__class__.moving_objects:
            
            # update position data of object depending on its motion mode
            obj.update_position(event)
            
            # Draw all artists of the object (if not, some can miss in motion)
            if self.__class__.blit:
                for artist in obj.all_artists:
                    ax.draw_artist(artist)

        # without this below, the graph is not updated
        if self.__class__.blit:
            canvas.blit(ax.bbox)
        else:
            canvas.draw()
            
            
    def initiate_motion(self, event):
        """Initiate motion and define leading artist that synchronizes plot.
        
        In particular, if there are several moving objects, save background
        (for blitting) only once. The line selected first becomes the leader
        for moving events, i.e. it is the one that detects mouse moving and 
        triggers re-drawing of all other moving lines.
        Note : all moving lines are necesary on the same axes"""
        
        if self.__class__.leader is None:
            self.__class__.leader = self
            # Below is to delay background setting for blitting until all
            # artists have been defined as animated.
            # This is because the canvas.draw() and/or canvas_copy_from_bbox()
            # calls need to be made with all moving artists declared as animated
            self.__class__.initiating_motion = True
            self.fig.canvas.draw()
            
        self.__class__.moving_objects.add(self)
        self.moving = True
        if self.__class__.blit:
            for artist in self.all_artists:
                artist.set_animated(True)
            
        # find which elements need to be active/updated during mouse motion
        self.set_active_info()
        # store location of pts and of click
        self.set_press_info(event)
        # set up dictionaries that store positions of elements during motion
        self.set_motion_tracking()
        
        # Transforms functions to go from px to data coords.
        # Need to be redefined if figure is resized or if zooming occurs
        self.datatopx = self.ax.transData.transform  # transform between data coords to px coords.
        self.pxtodata = self.ax.transData.inverted().transform  # pixels to data coordinates 
            
    
    def reset_after_motion(self):
        """Reset attributes that should be active only during motion."""
        
        self.picked_artists = set()
        self.active_info = {}
        self.press_info = {'currently_pressed': False}
        self.moving = False
        
        if self.__class__.blit:
            for artist in self.all_artists:
                artist.set_animated(False)
        
        # Reset class variables that store moving information
        self.__class__.moving_objects.remove(self)
        if self is self.__class__.leader:
            self.__class__.leader = None


    def update_position(self, position):
        """Update object position depending on moving mode and mouse position.
        
        Here it does not do much, but the method needs to be rewritten in
        subclassing to be useful. It is used by update_graph().
        """
        x, y = position
        
    
    def set_active_info(self):
        """Store information useful when in motion. Defined in subclasses."""
        active_info = {}
        return active_info
    
    
    def set_press_info(self, event):
        """Records information related to the mouse click, in px coordinates."""

        x = event.x
        y = event.y
       
        x_press = {'click': x}
        y_press = {'click': y}
        
        for pt in self.all_pts:
            xpt, ypt = self.get_pt_position(pt, 'px')
            x_press[pt] = xpt
            y_press[pt] = ypt
        
        self.press_info = x_press, y_press
        
    
    def set_motion_tracking(self):
        """set up dictionaries that store positions of elements during motion.
        
        Here, it stores data coordinates to not have to avoid multiple conversions.
        """
        x_inmotion = {}
        y_inmotion = {} 
        for pt in self.all_pts:
            xpt, ypt = self.get_pt_position(pt, 'data')
            x_inmotion[pt] =  xpt
            y_inmotion[pt] =  ypt
        self.x_inmotion = x_inmotion
        self.y_inmotion = y_inmotion
    
    
    def create(self):
        """Create object based on options. Need to be defined in subclass."""
        pass
    
    
    def eraser(self, option):
        """Private erasing function that is used by erase() and delete()"""
        
        for artist in self.all_artists:
            artist.remove()
        self.all_artists = []
        
        self.fig.canvas.draw()
        
        # Check if object is listed as still moving, and remove it.
        moving_objects = self.__class__.moving_objects
        if self in moving_objects:
            moving_objects.remove(self)
            
        if option == 'erase':
            pass
        elif option == 'delete':
            self.__class__.all_interactive_objects.remove(self)
            self.disconnect()
            if self.block:
                self.fig.canvas.stop_event_loop()    
        else:
            print('Warning: eraser function not called properly.')
            
                
    def erase(self):
        """Lighter than delete(), keeps object connected and referenced"""
        self.eraser('erase')
        
        
    def delete(self):
        """Hard delete of object by removing its components and references"""
        self.eraser('delete')
        
                
    def delete_others(self, *args):
        """Delete other instances of the same class (eccluding parents/children)
        
        Options 'all', 'fig', 'ax'. If no argument, assumes 'all'.
        """
        if len(args) == 0:
            option = 'all'
        else:
            option, *_ = args 
            
        all_instances = self.__class__.class_objects()
        
        if option == 'all':
            instances = all_instances
        elif option == 'fig':
            instances = [obj for obj in all_instances if obj.fig == self.fig]
        elif option == 'ax':
            instances = [obj for obj in all_instances if obj.ax == self.ax]
        else:
            raise ValueError(f"{option} is not a valid argument for delete_others(). "
                             "Possible values: 'all', 'fig', 'ax'.")

        others = set(instances) - {self}
        for other in others:
            other.delete()
            
            
    def get_pt_position(self, pt, option='data'):
        """Gets point position as a tuple from matplotlib line object.
        
        Options : 'data' (axis data coords, default) or 'px' (pixel coords).
        """
        # if orig=True (default), the format is not always consistent
        xpt, ypt = pt.get_data(orig=False)  
        # convert numpy array to scalar, faster than unpacking
        pos = xpt.item(), ypt.item()
        if option == 'data':
            return pos
        elif option == 'px':
            pos_px = self.datatopx(pos)
            return pos_px
        else:
            raise ValueError(f'{option} not a valid argument.')
            
    
    @classmethod
    def class_objects(cls):
        """Return all instances of a given class, excluding parent class."""
        # note : isinstance(obj, class) would also return the parent's objects
        instances = [obj for obj in cls.all_objects() if type(obj) is cls]
        return instances
    
    @classmethod
    def all_objects(cls):
        """Return all interactive objects, including parents and subclasses."""
        return cls.all_interactive_objects
            
    @classmethod
    def clear(cls):
        """Delete all interactive objects of the class and its subclasses."""
        objects = [obj for obj in cls.all_objects()]  # needed to avoid iterating over decreasing set
        for obj in objects:
            obj.delete()

    
# ================= connect/disconnect events and callbacks ==================

    def connect(self):
        """connect object to figure canvas events"""
        # mouse events
        self.cidpress = self.fig.canvas.mpl_connect('button_press_event', 
                                                    self.on_mouse_press)
        self.cidrelease = self.fig.canvas.mpl_connect('button_release_event',
                                                      self.on_mouse_release)
        self.cidpick = self.fig.canvas.mpl_connect('pick_event',
                                                   self.on_pick)
        self.cidmotion = self.fig.canvas.mpl_connect('motion_notify_event',
                                                     self.on_motion)    
        #key events
        self.cidpressk = self.fig.canvas.mpl_connect('key_press_event',
                                                     self.on_key_press)
        self.cidreleasek = self.fig.canvas.mpl_connect('key_release_event',
                                                     self.on_key_release)
        # figure events
        self.cidfigenter = self.fig.canvas.mpl_connect('figure_enter_event',
                                                      self.on_enter_figure)
        self.cidfigleave = self.fig.canvas.mpl_connect('figure_leave_event',
                                                      self.on_leave_figure)
        self.cidaxenter = self.fig.canvas.mpl_connect('axes_enter_event',
                                                      self.on_enter_axes)
        self.cidaxleave = self.fig.canvas.mpl_connect('axes_leave_event',
                                                      self.on_leave_axes)
        self.cidclose = self.fig.canvas.mpl_connect('close_event',
                                                    self.on_close)
        self.cidresize = self.fig.canvas.mpl_connect('resize_event',
                                                     self.on_resize)

    def disconnect(self):
        """disconnect callback ids"""    
        # mouse events
        self.fig.canvas.mpl_disconnect(self.cidpress)
        self.fig.canvas.mpl_disconnect(self.cidrelease)
        self.fig.canvas.mpl_disconnect(self.cidmotion)
        self.fig.canvas.mpl_disconnect(self.cidpick)
        # key events
        self.fig.canvas.mpl_disconnect(self.cidpressk)
        self.fig.canvas.mpl_disconnect(self.cidreleasek)
        # figure events
        self.fig.canvas.mpl_disconnect(self.cidfigenter)
        self.fig.canvas.mpl_disconnect(self.cidfigleave)
        self.fig.canvas.mpl_disconnect(self.cidaxenter)
        self.fig.canvas.mpl_disconnect(self.cidaxleave)
        self.fig.canvas.mpl_disconnect(self.cidclose)
        self.fig.canvas.mpl_disconnect(self.cidresize)


# ============================ callback functions ============================

# Need to be defined by the subclasses.

    # mouse events  ----------------------------------------------------------
    
    def on_mouse_press(self, event):
        print('Mouse Press')  # for testing
        print(f'data coords: {event.xdata, event.ydata}')  # for testing
        print(f'pixel coords: {event.x, event.y}')  # for testing
        print(' ')  # for testing
    
    def on_mouse_release(self, event):
        # Transforms functions to go from px to data coords.
        # Need to be redefined if figure is resized or if zooming occurs
        self.datatopx = self.ax.transData.transform  # transform between data coords to px coords.
        self.pxtodata = self.ax.transData.inverted().transform  # pixels to data coordinates  
    
    def on_pick(self, event):
        pass
 
    def on_motion(self, event):
        pass
    
    # key events  ------------------------------------------------------------
    
    def on_key_press(self, event):
        print(f'Key Press: {event.key}')
        pass
    
    def on_key_release(self, event):
        pass

    # figure events  ---------------------------------------------------------
    
    def on_enter_figure(self, event):
        pass

    def on_leave_figure(self, event):
        pass
    
    def on_enter_axes(self, event):
        pass

    def on_leave_axes(self, event):
        pass
    
    def on_resize(self, event):
        """When resizing, re-adjust the conversion from pixels to data pts."""
        # Transforms functions to go from px to data coords.
        # Need to be redefined if figure is resized or if zooming occurs
        self.datatopx = self.ax.transData.transform  # transform between data coords to px coords.
        self.pxtodata = self.ax.transData.inverted().transform  # pixels to data coordinates     

    def on_close(self, event):
        """Delete object if figure is closed"""
        self.delete()

    
    
if __name__ == '__main__':
    main()
    


