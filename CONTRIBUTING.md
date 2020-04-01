# Development information for Plot-OV (plov)


All Plot-OV (plov) classes use a **base class** named **InteractiveObject** located in the file *interactive_object.py*. It is not explicitly listed when importing the **plov** package. The only exception is **ClickFig**, which works differently (instead of moving objects on the figure, it selects the active axes by clicking on them), so it is a class on its own at the moment and will not be described here.

## General structure

- Events on a Matplotlib figure (click, mouse motion, key press, enter axes, etc.) are tied to *callback functions* through Matplotlib's event handling manager (see https://matplotlib.org/users/event_handling.html). This is managed by the base class with the `connect()` and `disconnect()` methods. Event data is passed to callbacks with the `event` parameter.

- Callback functions (`on_mouse_press`, `on_motion`, etc.) are defined, but empty in the base class, and need to be defined in subclasses.

- These callback functions call methods that are either base class methods or specific class methods (see below).

- Motion of objects is typically triggered by a picking (callback `on_pick`) or mouse press event (callback `on_mouse_press`) and is then managed by the callback function `on_motion`. **Cursor** works a little differently: it is always moving by default and deactivates when the mouse is pressed, to avoid display bugs that appear when zooming/panning in blitting mode.

- During motion, blitting is used for fast rendering. The principle is to save non-moving objects as a background pixel image and just re-draw moving objects on it. If blitting is deactivated with the `blit = False` option, all contents on the figure is re-drawn at every step, which is much slower and results in lag when many objects are present. The `cls.blit` bool attribute is managed by the base class and common to all subclasses, so that the last instance of any class defines whether blitting is used or not for all objects present.

- Because several objects can be moving at the same time (e.g. two lines dragged by the same click), display and blitting can be tricky and buggy. To solve this problem, one of the moving objects is defined as the leader. The leader object is stored in the `cls.leader` attribute of the base class, which is thus common to all subclasses. Only the leader calls graph update events, during which all other moving objects (stored in another class attribute `cls.moving_objects`) are updated at the same time.

- The tasks above are managed by `initiate_motion` (define leader) and `update_graph` (synchronized animation and blitting), two base class methods that call specific class methods when needed (see below).


## Base class

These methods and attributes are common to all subclasses but not all of them need to be called by subclasses. Be careful when modifying those, as they affect all subclasses.

### Instance methods
    
- `update_graph(event)` manages the motion of objects in the figure and should only be called by the `cls.leader` object (defined in `initiate_motion`, see below); other objects are drawn with a loop on all `moving_objects`. In subclasses, `update_graph` is typically called in the `on_motion` callback. 

- `initiate motion(event)` needs to be called before `update_graph` to define the leading object and store other useful info for motion. In particular, it calls the `set_press_info` and `set_active_info` methods that need to be defined in the subclass. An exception is for cursors, which are always moving by default, and which deactivate during the motion of other objects (lines, rectangles, etc.). Cursor objects, as a result, are never defined as leaders. `initiate motion` needs to be called in the subclass by another method or callback (typically `on_pick` or `on_press`) that itself already defines which objects will be moving (by adding them to `moving_objects`).

- `reset_after_motion()` basically reverses `initiate_motion` and other parameters.

- `delete()` and `erase()` cancel `create()` (which has to be defined in the subclasses, see below), temporarily for `erase` and permanently for `delete`.

- `delete_others(option)` applies `delete` to all other members of the same class, except `self`. Useful to have only one type of object on the figure (e.g. for cursors). Can be applied to all objects of the same class (`option='all'` or by simply calling `delete_others()`), all class objects in the same figure (option=`'fig'`), or all class objects in the same axes (`option='ax'`).

- `connect()`, `disconnect()`, and *callbacks*: see above.

### Class methods

- `class_objects()`: returns all instances of a given class, excluding parent/children class.
- `all_objects()`: returns all interactive objects, including parent/children/siblings etc.
- `clear()`: removes all interactive objects.

*Note*: A static_method `get_pt_position(pt)` also exists to return the position x, y (tuple) of a matplotlib single point from the matplotlib.lines.Line2D data.

### Class attributes

- `name`: should be also defined for every subclass, as it is used by the default `__repr__` and `__str__` defined in the base class.

- `all_interactives_objects`: stores all interactive objects of any class within **plov**. Objects are appended to this list during the init of the base class, so there is no need to do anything in the subclasses. In fact, subclasses *should not* define a class attribute with the same name. This attribute is the list returned when calling `cls.all_objects()`. 
 
- `moving_objects`: stores all objects (of any class) that need to be updated when calling `update_graph`. Objects should be added to this set by the subclasses themselves. Objects are removed from this set when calling `reset_after_motion` of the base class.

- `leader`: instance of any subclass that is the leading object for synchronized graph updating (see above). It is defined in `initiate_motion`, which blocks any other object to be defined as the leader until the leader is reset to `None`, e.g. when calling `reset_after_motion`.

- Blitting attributes: `blit` (bool, general blitting behavior, is defined by the last instance to be created), `background` (the pixel background currently used for blitting), `initiating_motion` (bool, will trigger background save for blitting in `update_graph` if True).

- `colors`: default class line colors, that are cycled through if necessary.


## Subclassing

### Subclass instance methods

The methods below are present in the base class but are (mostly) empty. They need to be redefined in each subclass to fit the needs of that specific class.

- `create()`: create the object. The minimal thing it needs to do is define the `all_artists` attribute, which is a list of all matplotlib artists the object is made of. Apart from this, its structure (number of arguments etc.) can be adapted for the needs of every subclass.

- `update_position(pos)` is called by `update_graph` to define how object of every specific class needs to be updated following the position of the mouse (only argument, tuple pos = x, y)

- `set_active_info`: generate information about the active object, e. g. its mode of motion and which parts of it need to be updated during motion, stored (either directly in the method or as a return of the method) in the dictionary `self.active_info`.

- `set_press_info`: generate information about the click, e. g. its position and the position the object relative to it, stored (either directly in the method or as a return of the method) in the dictionary `self.press_info`.

## Subclassing requirements

To summarize the information above, subclasses need to do the following things:

- define local `cls.name`,
- *do not* define local `cls.all_interactive_objects`, `cls.moving_objects`, `cls.leader`, `cls.initiating_motion`, `cls.blit`, `cls.background` so that when these values are called or updated, they are shared with the parent and sibling classes,
- *do not* append instance to global `cls.all_interactive_objects` (taken care of by the base class),
- append instance to global `cls.moving_objects` when motion or update is needed,
- redefine locally the `self.create`, `self.update_position`, `self.set_active_info`, `self.set_press_info` methods,
- define locally the callback functions and make them call the class methods,
- call `self.initiate_motion` (global) to define leader or check existing leader before motion,
- call `self.update_graph` (global) to create animation during motion or to trigger object update; for motion, make sure that only the leading object calls the method,
- call `self.reset_after_motion` after motion is done to reset things like leader, background, moving_objects and other info.

## Contributors

- Olivier Vincent