"""
homeassistant.components
~~~~~~~~~~~~~~~~~~~~~~~~

This package contains components that can be plugged into Home Assistant.

Component design guidelines:

Each component defines a constant DOMAIN that is equal to its filename.

Each component that tracks states should create state entity names in the
format "<DOMAIN>.<OBJECT_ID>".

Each component should publish services only under its own domain.

"""
import itertools as it
import importlib

import homeassistant as ha
import homeassistant.util as util

# Contains one string or a list of strings, each being an entity id
ATTR_ENTITY_ID = 'entity_id'

# String with a friendly name for the entity
ATTR_FRIENDLY_NAME = "friendly_name"

STATE_ON = 'on'
STATE_OFF = 'off'
STATE_NOT_HOME = 'not_home'
STATE_HOME = 'home'

SERVICE_TURN_ON = 'turn_on'
SERVICE_TURN_OFF = 'turn_off'

SERVICE_VOLUME_UP = "volume_up"
SERVICE_VOLUME_DOWN = "volume_down"
SERVICE_VOLUME_MUTE = "volume_mute"
SERVICE_MEDIA_PLAY_PAUSE = "media_play_pause"
SERVICE_MEDIA_NEXT_TRACK = "media_next_track"
SERVICE_MEDIA_PREV_TRACK = "media_prev_track"

_LOADED_COMP = {}


def _get_component(component):
    """ Returns requested component. Imports it if necessary. """

    comps = _LOADED_COMP

    # See if we have the module locally cached, else import it
    try:
        return comps[component]

    except KeyError:
        # If comps[component] does not exist, import module
        try:
            comps[component] = importlib.import_module(
                'homeassistant.components.'+component)

        except ImportError:
            # If we got a bogus component the input will fail
            comps[component] = None

        return comps[component]


def is_on(statemachine, entity_id=None):
    """ Loads up the module to call the is_on method.
    If there is no entity id given we will check all. """
    if entity_id:
        group = _get_component('group')

        entity_ids = group.expand_entity_ids([entity_id])
    else:
        entity_ids = statemachine.entity_ids

    for entity_id in entity_ids:
        domain = util.split_entity_id(entity_id)[0]

        module = _get_component(domain)

        try:
            if module.is_on(statemachine, entity_id):
                return True

        except AttributeError:
            # module is None or method is_on does not exist
            pass

    return False


def turn_on(bus, **service_data):
    """ Turns specified entity on if possible. """
    bus.call_service(ha.DOMAIN, SERVICE_TURN_ON, service_data)


def turn_off(bus, **service_data):
    """ Turns specified entity off. """
    bus.call_service(ha.DOMAIN, SERVICE_TURN_OFF, service_data)


def extract_entity_ids(statemachine, service):
    """
    Helper method to extract a list of entity ids from a service call.
    Will convert group entity ids to the entity ids it represents.
    """
    entity_ids = []

    if service.data and ATTR_ENTITY_ID in service.data:
        group = _get_component('group')

        # Entity ID attr can be a list or a string
        service_ent_id = service.data[ATTR_ENTITY_ID]
        if isinstance(service_ent_id, list):
            ent_ids = service_ent_id
        else:
            ent_ids = [service_ent_id]

        entity_ids.extend(
            ent_id for ent_id
            in group.expand_entity_ids(statemachine, ent_ids)
            if ent_id not in entity_ids)

    return entity_ids


def setup(bus, statemachine):
    """ Setup general services related to homeassistant. """

    def handle_turn_service(service):
        """ Method to handle calls to homeassistant.turn_on/off. """

        entity_ids = extract_entity_ids(statemachine, service)

        # Generic turn on/off method requires entity id
        if not entity_ids:
            return

        # Group entity_ids by domain. groupby requires sorted data.
        by_domain = it.groupby(sorted(entity_ids),
                               lambda item: util.split_entity_id(item)[0])

        for domain, ent_ids in by_domain:
            # Create a new dict for this call
            data = dict(service.data)

            # ent_ids is a generator, convert it to a list.
            data[ATTR_ENTITY_ID] = list(ent_ids)

            try:
                bus.call_service(domain, service.service, data)
            except ha.ServiceDoesNotExistError:
                # turn_on service does not exist
                pass

    bus.register_service(ha.DOMAIN, SERVICE_TURN_OFF, handle_turn_service)
    bus.register_service(ha.DOMAIN, SERVICE_TURN_ON, handle_turn_service)

    return True
