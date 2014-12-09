import kivy
import kivent_core
from kivent_core.gameworld import GameWorld
from kivy.config import Config
# Config.set('graphics', 'width', '1920')
# Config.set('graphics', 'height', '1080')
from flat_kivy import FlatApp
from kivy.base import EventLoop
from flat_kivy.ui_elements import FlatLabel, CheckBoxListItem, FlatCard
from flat_kivy.font_definitions import style_manager
from kivy_drivesync import DriveCarousel, start_drive_thread
from kivy.clock import Clock
from kivy.uix.widget import Widget        
import csv
from kivy.metrics import dp
from kivy.uix.screenmanager import Screen
from kivy.properties import StringProperty, ListProperty
from stores import stores, categories
from kivy.storage.jsonstore import JsonStore
from kivent_core.renderers import VertMesh, texture_manager
from math import pi, sin, cos
from datetime import datetime, timedelta
store_sentences = JsonStore('store_data.json')

FLIP_POS = False
MAP_HEIGHT = 2250
MAP_WIDTH = 4096

class StoreScreen(Screen):
    current_store = StringProperty(None)

    def on_current_store(self, instance, value):
        card_layout = self.ids.card_layout
        card_layout.clear_widgets()
        if value is not None:
            card_widget = stores[value]['page_card']
            card_layout.add_widget(card_widget)


class CategoryScreen(Screen):
    current_category = StringProperty(None)

class RootWidget(Widget):
    current_subcategories = ListProperty([])

    def __init__(self, **kwargs):
        self._map_ids = {}
        self._entity_map_ids = {}
        self._store_to_map_ids = {}
        self._highlighted_stores = []
        self._kiosks = []
        self._subcat_list_items = {}
        self.last_touch_time = None
        super(RootWidget, self).__init__(**kwargs)
        Clock.schedule_once(self.init_game)

    def ensure_startup(self):
        systems_to_check = ['map', 'renderer', 'position', 
            'gameview', 'color', 'scale', 'rotate', 'lerp']
        systems = self.gameworld.systems
        for each in systems_to_check:
            if each not in systems:
                return False
        return True

    def init_game(self, dt):
        if self.ensure_startup():
            self.setup_map()
            self.setup_states()
            self.set_state()
            self.load_stores()
            self.setup_kiosks()
            Clock.schedule_interval(self.update, 1./60.)
            

        else:
            Clock.schedule_once(self.init_game)

    def update(self, dt):
        self.gameworld.update(dt)

    def draw_regular_polygon(self, sides, radius, color):
        x, y = 0., 0.
        angle = 2. * pi / sides
        all_verts = []
        all_verts_a = all_verts.append
        l_pos = list((x, y))
        l_pos.extend(color)
        all_verts_a(l_pos)
        triangles = []
        triangles_a = triangles.extend
        r = radius
        for s in range(sides):
            new_pos = x + r * sin(s * angle), y + r * cos(s * angle)
            l_pos = list(new_pos)
            l_pos.extend((0., 0.))
            l_pos.extend(color)
            all_verts_a(l_pos)
            if s == sides-1:
                triangles_a((s+1, 0, 1))
            else:
                triangles_a((s+1, 0, s+2))
        render_system = self.gameworld.systems['renderer']
        vert_count = len(all_verts)
        index_count = len(triangles)
        vert_mesh =  VertMesh(render_system.attribute_count, 
            vert_count, index_count)
        vert_mesh.indices = triangles
        for i in range(vert_count):
            vert_mesh[i] = all_verts[i]
        return vert_mesh

    def setup_kiosks(self, do_render1=False, do_render2=True):
        kiosk_1_pos = (1280, 1260)
        gameview = self.gameworld.systems['gameview']
        pos1 = (1425., 1280.)
        size1 = (200., 50.)
        kiosk_color = tuple(
            FlatApp.get_running_app().get_color(('Pink', '500')))
        kiosk_ent = self.draw_kiosk(kiosk_1_pos, 25., kiosk_color,
            do_render=do_render1)
        self._kiosks.append(kiosk_ent)
        label = FlatLabel(size_hint=(None, None), size=size1,
            pos=pos1, text='You Are Here', style='Display 2')
        label.texture_update()
        texture_manager.load_texture('kiosk1', label.texture)
        label_ent = self.draw_label(pos1, size1, 'kiosk1', 
            color=(1., 1., 1., 1.), do_render=do_render1)
        self.correct_label_entity_rendering(label_ent)
        kiosk_2_pos = (2290., 1260.)
        kiosk_ent2 = self.draw_kiosk(kiosk_2_pos, 25., kiosk_color, 
            do_render=do_render2)
        self._kiosks.append(kiosk_ent2)
        pos2 = (2150., 1280.)
        label = FlatLabel(size_hint=(None, None), size=size1,
            pos=pos2, text='You Are Here', style='Display 2')
        label.texture_update()
        texture_manager.load_texture('kiosk2', label.texture)
        label_ent = self.draw_label(pos2, size1, 'kiosk2', 
            color=(1., 1., 1., 1.), do_render=do_render2)
        self.correct_label_entity_rendering(label_ent)
        

    def correct_label_entity_rendering(self, ent_id):
        gameworld = self.gameworld
        entities = gameworld.entities
        entity = entities[ent_id]
        render_comp = entity.renderer
        vert_mesh = render_comp.vert_mesh
        set_vert_att = vert_mesh.set_vertex_attribute
        set_vert_att(0, 2, 0.)
        set_vert_att(0, 3, 1.)
        set_vert_att(1, 2, 0.)
        set_vert_att(1, 3, 0.)
        set_vert_att(2, 2, 1.)
        set_vert_att(2, 3, 0.)
        set_vert_att(3, 2, 1.)
        set_vert_att(3, 3, 1.)



    def draw_label(self, pos, size, texture, color=(0., 0., 0., 1.),
        do_render=True, flip_pos=FLIP_POS):
        if flip_pos:
            pos = MAP_WIDTH - pos[0], MAP_HEIGHT - pos[1]
        create_component_dict= {
            'renderer': {'render': do_render, 
                'size': size, 'texture': texture},
            'position': pos,
            'color': color,
            'scale': 1.0,
            'rotate': 0.,
            }
        component_order = ['position', 'color', 'scale', 'rotate',
            'renderer']
        return self.gameworld.init_entity(create_component_dict, 
            component_order)

    def draw_kiosk(self, pos, radius, color, do_render=True, 
        flip_pos=FLIP_POS):
        vert_mesh = self.draw_regular_polygon(30, radius, color)
        if flip_pos:
            pos = MAP_WIDTH - pos[0], MAP_HEIGHT - pos[1]
        create_component_dict= {
            'renderer': {'render': do_render, 
                'vert_mesh': vert_mesh},
            'position': pos,
            'color': color,
            'scale': 1.0,
            'rotate': 0.,
            }
        component_order = ['position', 'color', 'scale', 'rotate',
            'renderer']
        return self.gameworld.init_entity(create_component_dict, 
            component_order)

    def draw_store(self, size, pos, color, flip_pos=FLIP_POS):
        pos = pos[0] + size[0]/2., pos[1]+size[1]/2.
        if flip_pos:
            pos = MAP_WIDTH - pos[0], MAP_HEIGHT - pos[1]
        create_component_dict = {
            'renderer': {'size': size,'render': True,}, 
            'position': pos, 'color': color, 'rotate': 0.,
            'scale': 1.0, 'lerp': {}}
        component_order = ['position', 'color', 'scale', 'rotate',
            'renderer', 'lerp']
        return self.gameworld.init_entity(create_component_dict, 
            component_order)

    def on_touch_down(self, touch):
        super(RootWidget, self).on_touch_down(touch)
        self.last_touch_time = self.get_time()

    def get_time(self):
        return datetime.utcnow()

    # def check_collision_with_map(self, screen_pos):
    #     gameworld = self.gameworld
    #     entities = gameworld.entities
    #     systems = gameworld.systems
    #     position_system = systems['position']
    #     entity_ids = position_system.entity_ids
    #     collided = []
    #     coll_a = collided.append
    #     gameview = systems['gameview']
    #     world_pos = gameview.convert_from_screen_to_world(screen_pos)
    #     #print(world_pos)
    #     def check_collide(world_pos, x, y, width, height):
    #         left_x = x - .5 * width
    #         right_x = x + .5 * width
    #         top_y = y + .5 * height
    #         bot_y = y - .5 * width

    #         wx, wy = world_pos
    #         if left_x < wx < right_x and bot_y < wy < top_y:
    #             #print(left_x, right_x, top_y, bot_y)
    #             return True
    #         else:
    #             return False

    #     for ent_id in entity_ids:
    #         entity = entities[ent_id]
    #         pos_comp = entity.position
    #         x, y = pos_comp.x, pos_comp.y
    #         render_comp = entity.renderer
    #         width, height = render_comp.width, render_comp.height
    #         if check_collide(world_pos, x, y, width, height):
    #             coll_a(ent_id)
    #     map_ids = self._entity_map_ids
    #     ent_ids = [map_ids[x] if x in map_ids else None for x in collided]



    # def on_touch_down(self, touch):
    #     gameview = self.gameworld.systems['gameview']
    #     world_pos = gameview.convert_from_screen_to_world(touch.pos)
    #     create_component_dict = {
    #         'renderer': {'size': (20, 20),'render': True,}, 
    #         'position': world_pos, 'color': (1., 0., 0., .75), 'rotate': 0.,
    #         'scale': 1.0}
    #     component_order = ['position', 'color', 'scale', 'rotate',
    #         'renderer', ]
    #     self.gameworld.init_entity(create_component_dict, 
    #         component_order)

    #     self.check_collision_with_map(touch.pos)
    #     super(RootWidget, self).on_touch_down(touch)

    def read_map_data(self, debug=False):

        with open('storemap.csv', 'rb') as csvfile:
            reader = csv.reader(csvfile, delimiter=' ', quotechar='|')
            self.map_data = map_data = {}
            map_ids = self._map_ids
            ent_map_ids = self._entity_map_ids
            ids = []
            for i, row in enumerate(reader):
                if i == 0:
                    ids = row[1].split(',')[:5]
                elif i < 131:
                    data = row[0].split(',')[:5]
                    color_to_use = FlatApp.get_running_app().get_color((
                        'DeepPurple', '600'))
                    ent_id = self.draw_store((float(data[1]), float(data[2])), 
                        (float(data[3]), float(data[4])), tuple(color_to_use))
                    if debug:
                        self.draw_store_label( 
                            (float(data[3]), float(data[4])), 
                            (float(data[1]), float(data[2])),
                             str(data[0]))
                    map_ids[data[0]] = ent_id
                    ent_map_ids[ent_id] = data[0]

                else:
                    pass

    def draw_store_label(self, pos, size, text):

        label = FlatLabel(size_hint=(None, None), size=size,
            pos=pos, text=text)
        label.texture_update()
        pos = pos[0] + size[0]/2., pos[1]+size[1]/2.
        key = 'store_text_' + text
        try:
            texture_manager.load_texture(key, label.texture)
        except:
            return
        label_ent = self.draw_label(pos, size, key, color=(1., 1., 1., 1.))
        self.correct_label_entity_rendering(label_ent)

    def get_stores_in_category(self, category):
        stores_to_return = []
        store_append = stores_to_return.append
        for store in stores:
            store_dict = stores[store]
            s_category = store_dict['store_category']
            if s_category == category:
                store_append(store)
        return stores_to_return

    def get_stores_subcategories(self, subcategories_list):
        stores_to_return = []
        store_append = stores_to_return.append
        subset_isect = set(subcategories_list).intersection
        for store in stores:
            store_dict = stores[store]
            subcategories = store_dict['sub_categories']
            intersect = subset_isect(set(subcategories))
            if len(intersect) > 0:
                store_append(store)
        return stores_to_return

    def on_current_subcategories(self, instance, value):
        stores_to_add = self.get_stores_subcategories(value)
        category_screen = self.ids.category_screen
        logo_layout = category_screen.ids.logo_layout
        for widget in logo_layout.children:
            widget.font_ramp_tuple = ('default', '1')
        logo_layout.clear_widgets()
        for store in stores_to_add:
            store_dict = stores[store]
            store_card = store_dict['store_card']
            store_card.font_ramp_tuple = ('current_logos', '1')
            logo_layout.add_widget(store_card)


    def setup_subcat_options(self, category):
        category_screen = self.ids.category_screen
        subcat_layout = category_screen.ids.subcat_options
        for widget in subcat_layout.children:
            widget.font_ramp_tuple = ('default', '1')
        subcat_layout.clear_widgets()
        self.current_subcategories = []
        new_subcategories = self.subcategories[category]
        subcat_list_items = self._subcat_list_items
        for new_sub in new_subcategories:
            if new_sub not in subcat_list_items:
                subcat_list_items[new_sub] =checkbox_item = CheckBoxListItem(
                text=categories[new_sub],
                font_ramp_tuple=('subcat', '1'), halign='right',
                size_hint=(1., .5), outline_color_tuple=('Cyan', '500'),
                checkbox_color_tuple=('Cyan', '900'), 
                font_color_tuple=('Gray', '0000'),
                check_color_tuple=('Cyan', '500'))
                checkbox_item.bind(active=self.handle_current_subcats)
                checkbox_item.sub_name = new_sub
            else:
                checkbox_item = subcat_list_items[new_sub]
                checkbox_item.font_ramp_tuple = ('subcat', '1')
            if not checkbox_item.ids.checkbox.active:
                checkbox_item.toggle_checkbox()
            else:
                self.handle_current_subcats(checkbox_item, True)
            subcat_layout.add_widget(checkbox_item)

    def handle_current_subcats(self, instance, value):
        current_subcategories = self.current_subcategories
        sub_name = instance.sub_name
        if value and sub_name not in current_subcategories:
            current_subcategories.append(sub_name)
        elif not value and sub_name in current_subcategories:
            current_subcategories.remove(sub_name)
            
    def load_stores(self):
        self.categories = categories = []
        self.subcategories = subcategories = {}
        store_to_map_ids = self._store_to_map_ids
        
        for store in stores:
            store_dict = stores[store]
            cat = store_dict['store_category']
            sub_cats = store_dict['sub_categories']
            if cat not in categories:
                categories.append(cat)
                subcategories[cat] = []
            for sub in sub_cats:
                if sub not in subcategories[cat]:
                    subcategories[cat].append(sub)
            map_keys = store_dict['mapkeys']
            if isinstance(map_keys, list):
                store_to_map_ids[store] = map_keys
            store_dict['store_card'] = card = FlatCard(
                text=store_dict['store_name'],
                image_source='assets/store_logos/' + store + '.png',
                size_hint=(.5, 1.),
                color_tuple=('Cyan', '500'),
                ripple_color_tuple=('Cyan', '100'),
                font_color_tuple=('Gray', '0000'),
                )
            card.store_key = store
            card.bind(on_release=self._open_store)
            try:
                card_text = store_sentences['store_data'][store]
            except:
                card_text = 'Not Found'
            store_dict['page_card'] = card2 = FlatCard(
                text=card_text,
                image_source='assets/store_fronts/' + store + '.jpg',
                color_tuple=('Cyan', '500'),
                ripple_color_tuple=('Cyan', '100'),
                font_color_tuple=('Gray', '0000'),)

    def _open_store(self, card):
        store = card.store_key
        app = FlatApp.get_running_app()
        app.open_store(store)
        self.highlight_store(store)
        box_tuple = self.calculate_size_for_store(store)
        self.look_at_box(*box_tuple)

    def highlight_store(self, store):
        self.clear_all_highlights()
        store_to_map_ids = self._store_to_map_ids
        gameworld = self.gameworld
        entities = gameworld.entities
        map_ids = self._map_ids
        highlighted_stores = self._highlighted_stores
        hstore_a = highlighted_stores.append
        lerp_system = gameworld.systems['lerp']
        render_system = gameworld.systems['renderer']
        app = FlatApp.get_running_app()
        if store in store_to_map_ids:
            map_keys = store_to_map_ids[store]
            if len(map_keys) == 0:
                
                app.raise_error('Sorry', 
                    'We did not find this store in our database.',
                    timeout=5.)
            for key in map_keys:
                try:
                    entity_id = map_ids[str(key)]
                except:
                    continue
                hstore_a(entity_id)
                render_system.rebatch_entity(entity_id)
                lerp_system.add_lerp_to_entity(entity_id, 'color', 'r', 1., 
                    1.5, 'float', callback=self.store_highlight_done)
                lerp_system.add_lerp_to_entity(entity_id, 'scale', 's', 1.3, 
                    1.5, 'float', callback=self.store_scale_done)
        else:
            app.raise_error('Sorry', 
                    'We did not find this store in our database.',
                    timeout=5.)

    def store_scale_done(self, entity_id, component, attribute, value):
        lerp_system = self.gameworld.systems['lerp']
        if value > 1.25:
            lerp_system.add_lerp_to_entity(entity_id, 'scale', 's', 1.,
                1.5, 'float', callback=self.store_scale_done)
        else:
            lerp_system.add_lerp_to_entity(entity_id, 'scale', 's', 1.3,
                1.5, 'float', callback=self.store_scale_done)

            
    def clear_all_highlights(self):
        highlighted_stores = self._highlighted_stores
        copy_of_hstores = [x for x in highlighted_stores]
        gameworld = self.gameworld
        lerp_system = gameworld.systems['lerp']
        hstore_remove = highlighted_stores.remove
        entities = gameworld.entities
        color_to_use = FlatApp.get_running_app().get_color((
            'DeepPurple', '600'))
        for ent_id in copy_of_hstores:
            lerp_system.clear_lerps_from_entity(ent_id)
            hstore_remove(ent_id)
            entity = entities[ent_id]
            color_comp = entity.color
            scale_comp = entity.scale
            color_comp.r = color_to_use[0]
            scale_comp.s = 1.


    def store_highlight_done(self, entity_id, component, attribute, value):
        lerp_system = self.gameworld.systems['lerp']
        color_to_use = FlatApp.get_running_app().get_color((
            'DeepPurple', '600'))
        if value > .95:
            lerp_system.add_lerp_to_entity(entity_id, 'color', 'r', 
                color_to_use[0],
                1.5, 'float', callback=self.store_highlight_done)
        else:
            lerp_system.add_lerp_to_entity(entity_id, 'color', 'r', 1.,
                1.5, 'float', callback=self.store_highlight_done)


    def focus_store(self, store):
        pass


    def state_change_callback(self, state_name, previous_state):
        if state_name == 'bathroom_screen':
            self.highlight_store('bathrooms')
        elif state_name == 'main':
            self.clear_all_highlights()
        elif state_name == 'directory_screen':
            self.clear_all_highlights()
        self.calculate_gameview_height(state_name)

    def on_size(self, instance, value):
        if self.ensure_startup():
            self.calculate_gameview_height(self.gameworld.state)
        
    def calculate_gameview_height(self, state_name):
        gameworld = self.gameworld
        systems = gameworld.systems
        gameview = systems['gameview']
        mapsystem = systems['map']
        mapsize = mapsystem.map_size

        if state_name == 'bathroom_screen':
            gameview.width = self.width
            gameview.height = self.height - dp(90) - self.height * .025
            gameview.y = self.height * .025 + dp(90)
            gameview.x = 0.
            #print(mapsize, self.width)
            box_tuple = self.calculate_size_for_store('bathrooms')
            self.look_at_box(*box_tuple)
            
        elif state_name == 'directory_screen':
            categories_screen = self.ids.directory_categories_screen
            scrollview = categories_screen.ids.scroll
            gameview.width = self.width * .49
            gameview.x = self.width *.255
            
            gameview.y = scrollview.height + scrollview.y + dp(10)
            gameview.height = self.height - gameview.y - dp(10)
            gameview.camera_scale = max(float(mapsize[0])/gameview.width,
                float(mapsize[1])/gameview.height)
            gameview.look_at((mapsize[0]/2. - 200.,
                mapsize[1]/2. - 450.))
        elif state_name == 'store_screen':
            store_screen = self.ids.store_screen
            back_button = store_screen.ids.back_button
            gameview.width = self.width * .6 - dp(10)
            gameview.x = self.width * .40
            gameview.height = self.height - (
                back_button.height + back_button.y + dp(25))
            gameview.y = back_button.height + back_button.y + dp(15)
            # gameview.camera_scale = float(mapsize[1])/gameview.height
            # gameview.look_at((mapsize[0]/2. - gameview.x,
            #     mapsize[1]/2. - gameview.y))

    def calculate_size_for_store(self, store):
        kiosks = self._kiosks
        y_points = []
        x_points = []
        y_a = y_points.append
        x_a = x_points.append
        gameworld = self.gameworld
        entities = gameworld.entities
        radius = 25.
        margin = 0.
        for ent_id in kiosks:
            entity = entities[ent_id]
            pos_comp = entity.position
            x, y = pos_comp.x, pos_comp.y
            max_x = x + radius + margin
            x_a(max_x)
            min_x = x - radius - margin
            x_a(min_x)
            max_y = y + radius + margin
            y_a(max_y)
            min_y = y - radius - margin
            y_a(min_y)
        store_to_map_ids = self._store_to_map_ids
        map_ids = self._map_ids
        if store in store_to_map_ids:
            map_keys = store_to_map_ids[store]
            for key in map_keys:
                try:
                    entity_id = map_ids[str(key)]
                except:
                    continue
                entity = entities[entity_id]
                pos_comp = entity.position
                render_comp = entity.renderer
                width, height = render_comp.width, render_comp.height
                width = width *.5
                height = height *.5
                x, y = pos_comp.x, pos_comp.y
                max_x = x + width + margin
                x_a(max_x)
                min_x = x - width - margin
                x_a(min_x)
                max_y = y + height + margin
                y_a(max_y)
                min_y = y - height - margin
                y_a(min_y)
        
        t_min_y = min(y_points)
        t_max_y = max(y_points)
        t_min_x = min(x_points)
        t_max_x = max(x_points)
        return(t_min_x, t_max_x, t_min_y, t_max_y)

            
    def look_at_box(self, min_x, max_x, min_y, max_y):
        systems = self.gameworld.systems
        gameview = systems['gameview']
        width = max_x - min_x
        height = max_y - min_y
        mapsystem = systems['map']
        gameview.camera_scale = 2*width/gameview.width
        scale = gameview.camera_scale
        mapsize = mapsystem.map_size
        cx = min_x + (width * .5) - gameview.x/scale
        cy = min_y + (height * .5) - gameview.y/scale

        gameview.look_at((cx, cy))


    def setup_states(self):
        self.gameworld.add_state(state_name='main', 
            systems_added=[],
            systems_removed=['renderer'], 
            systems_paused=['renderer'],
            systems_unpaused=[],
            screenmanager_screen='front_page',
            on_change_callback=self.state_change_callback)
        self.gameworld.add_state(state_name='bathroom_screen',
            systems_added=['renderer'],
            systems_removed=[],
            systems_paused=[],
            systems_unpaused=['renderer'],
            screenmanager_screen='bathroom',
            on_change_callback=self.state_change_callback)
        self.gameworld.add_state(state_name='directory_screen',
            systems_added=['renderer'],
            systems_removed=[],
            systems_paused=[],
            systems_unpaused=['renderer'],
            screenmanager_screen='directory_categories', 
            on_change_callback=self.state_change_callback,)
        self.gameworld.add_state(state_name='category_screen',
            systems_removed=['renderer'], systems_paused=['renderer'],
            screenmanager_screen='category',
            on_change_callback=self.state_change_callback,)
        self.gameworld.add_state(state_name='store_screen',
            systems_added=['renderer'],
            systems_unpaused=['renderer'],
            screenmanager_screen='store', 
            on_change_callback=self.state_change_callback,)

    def setup_map(self):
        gameworld = self.gameworld
        gameworld.currentmap = gameworld.systems['map']

    def set_state(self):
        self.gameworld.state = 'main'
        self.read_map_data()


ad_mapping = {
    'clothing': ('ClothingAds_Left', 'ClothingAds_Right'),
    'beauty': ('BeautyAds_Left', 'BeautyAds_Right'),
    'accessories': ('AccessoryAds_Left', 'AccessoryAds_Right'),
    'food': ('FoodAds_Left', 'FoodAds_Right'),
    'jewelry': ('JewelryAds_Left', 'JewelryAds_Right'),
    'movies': ('MovieAds_Left', 'MovieAds_Right'),
    'shoes': ('ShoeAds_Left', 'ShoeAds_Right'),
    'electronics': ('ElectronicsAds_Left', 'ElectronicsAds_Right'),
    'home': ('HomeAds_Left', 'HomeAds_Right'),
    'gifts': ('GiftAds_Left', 'GiftAds_Right'),
}


class MallKioskApp(FlatApp):

    def __init__(self, **kwargs):
        self.setup_font_ramps()
        self._category_carousels = {}
        super(MallKioskApp, self).__init__(**kwargs)
        self.setup_themes()
        self.time_to_reset = 3
        Clock.schedule_interval(self.reset, 30.)
        
    def build(self):
        folders_to_track = ['FrontPageAds', 
            'DirectoryCategories_Right', 'DirectoryCategories_Left']
        folders_e = folders_to_track.extend
        for each in ad_mapping:
            folders_e(ad_mapping[each])
        start_drive_thread(folders_to_track, __file__)
        EventLoop.window.bind(on_keyboard=self.hook_keyboard)

    def change_screen(self, name):
        self.root.gameworld.state = name

    def open_store(self, store):
        store_screen = self.root.ids.store_screen
        store_screen.current_store = store
        self.change_screen('store_screen')


    def get_time(self):
        return datetime.utcnow()

    def reset(self, dt):
        last_touch_time = self.root.last_touch_time
        current_time = self.get_time()
        time_to_reset = timedelta(minutes=self.time_to_reset)
        if last_touch_time is not None:
            if last_touch_time + time_to_reset < current_time:
                self.change_screen('main')

    def open_category(self, category):
        category_screen = self.root.ids.category_screen
        category_screen.current_category = category
        ad_left = category_screen.ids.ad_left
        ad_right = category_screen.ids.ad_right
        ad_right.clear_widgets()
        ad_left.clear_widgets()
        category_carousels = self._category_carousels
        if category in ad_mapping:
            if category not in category_carousels:
                category_data = category_carousels[category] = {}
                category_data['left'] = carousel_left = DriveCarousel(
                    size_hint=(1., 1.),
                    pyfile=__file__,
                    folders_to_track=[ad_mapping[category][0]],
                    loop=True)
                
                category_data['right'] = carousel_right = DriveCarousel(
                    size_hint=(1., 1.),
                    pyfile=__file__,
                    pos_hint={'x': 0.},
                    folders_to_track=[ad_mapping[category][1]],
                    loop=True)
            else:
                category_data = category_carousels[category]
                carousel_left = category_data['left']
                carousel_right = category_data['right']
            ad_left.add_widget(carousel_left)
            ad_right.add_widget(carousel_right)
        self.root.setup_subcat_options(category)
        self.change_screen('category_screen')

    def on_start(self):
        drive_carousel = DriveCarousel(
            size_hint=(.4, .8),
            pos_hint={'x': .575, 'y':.1},
            pyfile=__file__,
            folders_to_track=['FrontPageAds'],
            loop=True)
        self.root.ids.front_page_screen.add_widget(drive_carousel)
        drive_carousel = DriveCarousel(
            size_hint=(1., 1.),
            pos_hint={'x':0.},
            pyfile=__file__,
            folders_to_track=['DirectoryCategories_Right'],
            loop=True)
        categories_screen = self.root.ids.directory_categories_screen
        categories_screen.ids.ad_right.add_widget(drive_carousel)
        drive_carousel = DriveCarousel(
            size_hint=(1., 1.),
            pyfile=__file__,
            folders_to_track=['DirectoryCategories_Left'],
            loop=True)
        categories_screen.ids.ad_left.add_widget(drive_carousel)

    def hook_keyboard(self, window, key, *largs):
        if key == 27:
            return True

    def setup_font_ramps(self):
        font_styles = {
            'Display 4': {
                'font': 'Roboto-Light.ttf', 
                'sizings': {'mobile': (112, 'sp'), 'desktop': (112, 'sp')},
                'alpha': .8,
                'wrap': False,
                }, 
            'Display 3': {
                'font': 'Roboto-Regular.ttf', 
                'sizings': {'mobile': (56, 'sp'), 'desktop': (56, 'sp')},
                'alpha': .8,
                'wrap': False,
                },
            'Display 2': {
                'font': 'Roboto-Regular.ttf', 
                'sizings': {'mobile': (45, 'sp'), 'desktop': (45, 'sp')},
                'alpha': .8,
                'wrap': True,
                'wrap_id': '1',
                'leading': (48, 'pt'),
                },
            'Display 1': {
                'font': 'Roboto-Regular.ttf', 
                'sizings': {'mobile': (34, 'sp'), 'desktop': (34, 'sp')},
                'alpha': .8,
                'wrap': True,
                'wrap_id': '2',
                'leading': (40, 'pt'),
                },
            'Headline': {
                'font': 'Roboto-Regular.ttf', 
                'sizings': {'mobile': (24, 'sp'), 'desktop': (24, 'sp')},
                'alpha': .9,
                'wrap': True,
                'wrap_id': '3',
                'leading': (32, 'pt'),
                },
            'Title': {
                'font': 'Roboto-Medium.ttf', 
                'sizings': {'mobile': (20, 'sp'), 'desktop': (20, 'sp')},
                'alpha': .9,
                'wrap': False,
                },
            'Subhead': {
                'font': 'Roboto-Regular.ttf', 
                'sizings': {'mobile': (16, 'sp'), 'desktop': (15, 'sp')},
                'alpha': .9,
                'wrap': True,
                'wrap_id': '4',
                'leading': (28, 'pt'),
                },
            'Body 2': {
                'font': 'Roboto-Medium.ttf', 
                'sizings': {'mobile': (14, 'sp'), 'desktop': (13, 'sp')},
                'alpha': .9,
                'wrap': True,
                'wrap_id': '5',
                'leading': (24, 'pt'),
                },
            'Body 1': {
                'font': 'Roboto-Regular.ttf', 
                'sizings': {'mobile': (14, 'sp'), 'desktop': (13, 'sp')},
                'alpha': .9,
                'wrap': True,
                'wrap_id': '6',
                'leading': (20, 'pt'),
                },
            'Caption': {
                'font': 'Roboto-Regular.ttf', 
                'sizings': {'mobile': (12, 'sp'), 'desktop': (12, 'sp')},
                'alpha': .8,
                'wrap': False,
                },
            'Menu': {
                'font': 'Roboto-Medium.ttf', 
                'sizings': {'mobile': (14, 'sp'), 'desktop': (13, 'sp')},
                'alpha': .9,
                'wrap': False,
                },
            'Button': {
                'font': 'Roboto-Medium.ttf', 
                'sizings': {'mobile': (14, 'sp'), 'desktop': (14, 'sp')},
                'alpha': .9,
                'wrap': False,
                },
            }
        for each in font_styles:
            style = font_styles[each]
            sizings = style['sizings']
            style_manager.add_style(style['font'], each, sizings['mobile'], 
                sizings['desktop'], style['alpha'])

        style_manager.add_font_ramp('1', ['Display 2', 'Display 1', 
            'Headline', 'Subhead', 'Body 2', 'Body 1'])

    def setup_themes(self):
        pass



if __name__ == '__main__':
    MallKioskApp().run()