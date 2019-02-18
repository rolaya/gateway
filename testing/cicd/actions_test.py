import unittest
import time
import urllib
import logging
import simplejson as json
from random import randint
from toolbox import exception_handler

LOGGER = logging.getLogger('openmotics')
#                                            _   _
#                                           | | (_)
#    ___  _ __   ___ _ __    _ __ ___   ___ | |_ _  ___ ___
#   / _ \| '_ \ / _ \ '_ \  | '_ ` _ \ / _ \| __| |/ __/ __|
#  | (_) | |_) |  __/ | | | | | | | | | (_) | |_| | (__\__ \
#   \___/| .__/ \___|_| |_| |_| |_| |_|\___/ \__|_|\___|___/
#        | |
#        |_|


class ActionsTest(unittest.TestCase):
    webinterface = None
    tools = None
    token = ''
    TESTEE_POWER = 8
    ROOM_NUMBER = 5
    GROUP_ACTION_CONFIG = '240,0,244,{0},240,10,161,{0},235,5,160,{0},235,255,240,20,160,{0},235,5,161,{0},235,255,240,255'
    FLOOR_NUMBER = 3
    GROUP_ACTION_TARGET_ID = 0
    INPUT_COUNT = 8

    @classmethod
    def setUpClass(cls):
        if not cls.tools.healthy_status:
            raise unittest.SkipTest('The Testee is showing an unhealthy status. All tests are skipped.')
        cls.token = cls.tools._get_new_token('openmotics', '123456')

    def setUp(self):
        if not self.tools.discovery_success:
            self.tools.discovery_success = self.tools._assert_discovered(self.token, self.webinterface)
            if not self.tools.discovery_success:
                self.skipTest('Failed to discover modules.')
        LOGGER.info('Running: {}'.format(self.id()))

    @unittest.skip('Currently skipped due to loudness.')
    @exception_handler
    def test_do_group_action_on_off(self):
        """ Testing the execution of all configured group actions on the testee. """
        self._set_group_actions_config(self.token)
        response_json = self.tools._api_testee('get_group_action_configurations', self.token)
        config = response_json.get('config')
        self.assertIsNotNone(config, 'Should return the config of the group actions.')
        self.assertTrue(bool(config), 'The config should not be empty when returned from get group action configurations API. Got: {0}'.format(response_json))
        configured_actions = []
        for one in config:
            if one.get('actions') is not None or one.get('actions') != '':
                configured_actions.append(one)

        for one in configured_actions:
            url_params = urllib.urlencode({'group_action_id': one.get('id')})
            self.tools._api_testee('do_group_action?{0}'.format(url_params), self.token)
        pressed_inputs = json.loads(self.webinterface.get_last_inputs()).get('inputs')
        self.assertIsNotNone(pressed_inputs)
        self.assertTrue(pressed_inputs)

    @exception_handler
    def test_do_group_action_on_off_authorization(self):
        """ Testing do_group_action API auth verification. """
        response_json = self.tools._api_testee('get_group_action_configurations', 'some_token', expected_failure=True)
        self.assertEquals(response_json, 'invalid_token',
                          'Should not be able to return group action configurations without a valid token. Got: {0}'.format(response_json))

        response_json = self.tools._api_testee('get_output_status', 'some_token', expected_failure=True)
        self.assertEquals(response_json, 'invalid_token',
                          'The get_group_action_configurations API call should return \'invalid_token\' when called with an invalid token. Got: {0}'.format(response_json))

        invalid_group_action_id = 9999
        url_params = urllib.urlencode({'group_action_id': invalid_group_action_id})
        response_json = self.tools._api_testee('do_group_action?{0}'.format(url_params), self.token, expected_failure=True)
        self.assertEquals(response_json.get('msg'), 'group_action_id not in [0, 160]: {0}'.format(invalid_group_action_id), 'Should return an error message when calling do group action API with an invalid group action ID. Got: {0}'.format(response_json))

    @exception_handler
    def test_set_group_action_configuration(self):
        """ Testing the setting up of one group action. """
        time.sleep(0.5)
        i = randint(0, 159)
        one_group_action_config = {'id': i,
                                   'actions': self.GROUP_ACTION_CONFIG.format(0),
                                   'name': 'Test' + str(i)}
        url_params = urllib.urlencode({'config': json.dumps(one_group_action_config)})  # Will turn on output 0 if it's off and turn it back off, reverse if it's on already.

        self.tools._api_testee('set_group_action_configuration?{0}'.format(url_params), self.token)

        url_params = urllib.urlencode({'id': i})
        response_json = self.tools._api_testee('get_group_action_configuration?{0}'.format(url_params), self.token)
        self.assertEquals(response_json.get('config'), one_group_action_config, 'The new config should be the same as the present group action config. Got: returned: {0} configured: {1}'.format(response_json.get('config'), one_group_action_config))

        url_params = urllib.urlencode({'group_action_id': i})
        self.tools._api_testee('do_group_action?{0}'.format(url_params), self.token)

        self.assertTrue(self._check_if_event_is_captured(self.GROUP_ACTION_TARGET_ID, time.time(), 1), 'Should return true after calling do_group_action API. Got: {0}'.format(self.tools.input_status))

        self.assertTrue(self._check_if_event_is_captured(self.GROUP_ACTION_TARGET_ID, time.time(), 0), 'Should untoggled output 0 after a moment and must show input releases. Got: {0}'.format(self.tools.input_status))

    @exception_handler
    def test_set_group_action_configuration_authorization(self):
        """ Testing the setting up of one group action auth verification. """
        response_json = self.tools._api_testee('set_group_action_configuration', 'some_token', expected_failure=True)
        self.assertEquals(response_json, 'invalid_token',
                          'Should be True after setting the group action configuration. Got: {0}'.format(response_json))

    @exception_handler
    def test_set_group_action_configurations(self):
        """ Testing the setting up of all configurable group actions ( all = 160 available group actions configurations ) """
        _, config = self._set_group_actions_config(self.token)

        response_json = self.tools._api_testee('get_group_action_configurations', self.token)
        self.assertEquals(response_json.get('config'), config)

    @exception_handler
    def test_set_group_action_configurations_authorization(self):
        """ Testing set_group_action_configurations auth verification """
        response_json = self.tools._api_testee('set_group_action_configurations', 'some_token', expected_failure=True)
        self.assertEquals(response_json, 'invalid_token')

        response_json = self.tools._api_testee('get_group_action_configurations', 'some_token', expected_failure=True)
        self.assertEquals(response_json, 'invalid_token')

    @exception_handler
    def test_set_startup_action_configuration(self):
        """ Testing the setting up of the startup action configuration. """
        config = {"actions": self.GROUP_ACTION_CONFIG.format(0)}
        url_params = urllib.urlencode({'config': json.dumps(config)})

        self.tools._api_testee('set_startup_action_configuration?{0}'.format(url_params), self.token)

        response_json = self.tools._api_testee('get_startup_action_configuration', self.token)
        self.assertEquals(response_json.get('config'), config, 'The new config should be the same as the present startup action config. Got{0}'.format(response_json))

        response_json = json.loads(self.webinterface.get_output_status())

        status_list = response_json.get('status', [])
        self.assertTrue(bool(status_list), 'Should contain the list of output statuses. Got: {0}'.format(status_list))
        if status_list[8].get('status') == 0:
            json.loads(self.webinterface.set_output(id=self.TESTEE_POWER, is_on=True))
        else:
            json.loads(self.webinterface.set_output(id=self.TESTEE_POWER, is_on=False))
            time.sleep(0.5)
            json.loads(self.webinterface.set_output(id=self.TESTEE_POWER, is_on=True))
        self.assertTrue(self._check_if_event_is_captured(self.GROUP_ACTION_TARGET_ID, time.time(), 1), 'Should execute startup action and turn output 0 on, Tester\'s input will see a press')

        self.assertTrue(self._check_if_event_is_captured(self.GROUP_ACTION_TARGET_ID, time.time(), 0), 'Should execute startup action and turn output 0 off, Tester\'s input will see a press')

        self.tools.token = self.tools._get_new_token('openmotics', '123456')

    @exception_handler
    def test_set_startup_action_configuration_authorization(self):
        """ Testing the setting up of the startup action configuration. """
        response_json = self.tools._api_testee('set_startup_action_configuration', 'some_token', expected_failure=True)
        self.assertEquals(response_json, 'invalid_token')

    @exception_handler
    def test_do_basic_action(self):
        """ Testing if do basic action API call and execution works. """
        i = randint(0, 7)
        url_params = urllib.urlencode(
            {'action_type': 165, 'action_number': i})  # ActionType 165 turns on an output.
        self.tools._api_testee('do_basic_action?{0}'.format(url_params), self.token)
        self.assertTrue(self._check_if_event_is_captured(i, time.time(), 1), 'Should have toggled the tester\'s input. Got {0}, expected output ID to toggle: {1}'.format(self.tools.input_status, i))

        url_params = urllib.urlencode({'action_type': 160, 'action_number': i})  # ActionType 160 turns off an output.
        self.tools._api_testee('do_basic_action?{0}'.format(url_params), self.token)

        self.assertTrue(self._check_if_event_is_captured(i, time.time(), 0), 'Should have unpressed the tester\'s input. Got {0}, expected output ID to untoggle: {1}'.format(self.tools.input_status, i))
        self.tools._api_testee('get_output_status', self.token)

    @exception_handler
    def test_do_basic_action_authorization(self):
        """ Testing do basic action API auth verification. """
        response_json = self.tools._api_testee('do_basic_action', 'some_token', expected_failure=True)
        self.assertEquals(response_json, 'invalid_token')

        url_params = urllib.urlencode({'action_type': 165, 'action_number': 46})
        response_json = self.tools._api_testee('do_basic_action?{0}'.format(url_params), 'some_token', expected_failure=True)
        self.assertEquals(response_json, 'invalid_token')

    @exception_handler
    def test_motion_sensor_timer_short(self):
        """ Testing the setting up of a virtual motion sensor and validating the timer setting ( short = 2m30s ) """
        i = randint(0, 7)

        modified_config = {'name': 'MotionS',
                           'basic_actions': '195,{0}'.format(i),
                           'invert': 255,
                           'module_type': 'I',
                           'can': '',
                           'action': 240,
                           'id': i,
                           'room': 255}

        url_params = urllib.urlencode({'config': json.dumps(modified_config)})
        self.tools._api_testee('set_input_configuration?{0}'.format(url_params), self.token)

        self.webinterface.set_output(id=i, is_on=True)  # Sensor detects movement
        time.sleep(0.2)
        self.webinterface.set_output(id=i, is_on=False)  # Sensor stops detecting movement

        start = time.time()
        time.sleep(0.3)
        self.assertTrue(self._check_if_event_is_captured(i, time.time(), 1), 'Should turn on an input on the Tester that act as a motion sensor.')

        result = self._check_if_event_is_captured(i, time.time(), 0)

        end = time.time()
        self.assertTrue(result, 'Should have unpressed the tester\'s input. Got {0}, expected output ID to untoggle: {1}'.format(result, i))
        self.assertTrue(158 > end - start > 148, 'Should toggle off after around 2m30s. Got: {0}'.format(end - start))

    @exception_handler
    def test_get_input_configuration_authorization(self):
        """ Testing if getting input configurations works without a valid authorization. """
        url_params = urllib.urlencode({'id': 3})

        response_json = self.tools._api_testee('get_input_configuration?{0}'.format(url_params), 'some_token', expected_failure=True)
        self.assertEquals(response_json, 'invalid_token',
                          'Expecting the response to be invalid_token. Got: {0}'.format(response_json))

        response_json = self.tools._api_testee('get_input_configurations', 'some_token', expected_failure=True)
        self.assertEquals(response_json, 'invalid_token',
                          'Expecting the response to be invalid_token. Got: {0}'.format(response_json))

    @exception_handler
    def test_execute_group_action(self):
        """ Testing the execution of a group action that toggles output 0. """
        self._set_group_actions_config(self.token)

        input_number = randint(0, 7)
        group_action_number = randint(0, 159)
        config = {'name': 'input_ex',
                  'basic_actions': '2,{0}'.format(group_action_number),
                  'invert': 255,
                  'module_type': 'I',
                  'can': '',
                  'action': 240,
                  'id': input_number,
                  'room': 255}
        url_params = urllib.urlencode({'config': json.dumps(config)})
        self.tools._api_testee('set_input_configuration?{0}'.format(url_params), self.token)
        self.webinterface.set_output(id=input_number, is_on=True)
        self.assertTrue(self._check_if_event_is_captured(0, time.time(), 1), 'Should execute a group action to toggle on output 0.')

        self.webinterface.set_output(id=input_number, is_on=False)
        self.assertTrue(self._check_if_event_is_captured(0, time.time(), 0), 'Should execute a group action to toggle off output 0 after a while.')

    @exception_handler
    def test_toggles_output(self):
        """ Testing toggling one output. """
        time.sleep(0.3)
        output_to_toggle = randint(0, 7)
        config = {'name': 'input_to',
                  'basic_actions': '162,{0}'.format(output_to_toggle),
                  'invert': 255,
                  'module_type': 'I',
                  'can': '',
                  'action': 240,
                  'id': output_to_toggle,
                  'room': 255}
        url_params = urllib.urlencode({'config': json.dumps(config)})
        self.tools._api_testee('set_input_configuration?{0}'.format(url_params), self.token)

        self.webinterface.set_output(id=output_to_toggle, is_on=True)  # Toggling the Tester's output, The Testee's input will see a press that executes an action that toggles an output, to confirm the output toggling, we can check the Tester's input module (all modules are cross configured).
        self.assertTrue(self._check_if_event_is_captured(output_to_toggle, time.time(), 1), 'The Tester\'s input module should see a press after toggling the Testee\'s output. Got: {0}'.format(self.tools.input_status))
        time.sleep(0.3)
        self.webinterface.set_output(id=output_to_toggle, is_on=False)
        self.assertTrue(self._check_if_event_is_captured(output_to_toggle, time.time(), 1), 'The Tester\'s input module should keep seeing a press after toggling the Testee\'s output. Got: {0}'.format(self.tools.input_status))
        time.sleep(0.3)
        self.webinterface.set_output(id=output_to_toggle, is_on=True)  # Toggling the Tester's output, The Testee's input will see a press that executes an action that toggles an output, to confirm the output toggling, we can check the Tester's input module (all modules are cross configured).
        self.assertTrue(self._check_if_event_is_captured(output_to_toggle, time.time(), 0), 'The Tester\'s input module should see a release after toggling the Testee\'s output. Got: {0}'.format(self.tools.input_status))
        time.sleep(0.3)
        self.webinterface.set_output(id=output_to_toggle, is_on=False)
        self.assertTrue(self._check_if_event_is_captured(output_to_toggle, time.time(), 0), 'The Tester\'s input module should keep seeing a release after toggling the Testee\'s output. Got: {0}'.format(self.tools.input_status))

    @exception_handler
    def test_turn_output_on_off(self):
        """ Testing turning one output on and off. """
        time.sleep(0.3)
        output_to_toggle = randint(0, 7)
        config = {'name': 'input_to',
                  'basic_actions': '161,{0}'.format(output_to_toggle),
                  'invert': 255,
                  'module_type': 'I',
                  'can': '',
                  'action': 240,
                  'id': output_to_toggle,
                  'room': 255}
        url_params = urllib.urlencode({'config': json.dumps(config)})
        self.tools._api_testee('set_input_configuration?{0}'.format(url_params), self.token)

        self.webinterface.set_output(id=output_to_toggle, is_on=True)  # Toggling the Tester's output, The Testee's input will see a press that executes an action that toggles an output, to confirm the output toggling, we can check the Tester's input module (all modules are cross configured).
        self.assertTrue(self._check_if_event_is_captured(output_to_toggle, time.time(), 1), 'The Tester\'s input module should see a press after toggling the Testee\'s output. Got: {0}'.format(self.tools.input_status))
        time.sleep(0.3)
        self.webinterface.set_output(id=output_to_toggle, is_on=False)
        self.assertTrue(self._check_if_event_is_captured(output_to_toggle, time.time(), 1), 'Even if the Tester\'s output is off, the Testee\'s input should keep seeing a press. Got: {0}'.format(self.tools.input_status))

        config = {'name': 'input_to',
                  'basic_actions': '160,{0}'.format(output_to_toggle),
                  'invert': 255,
                  'module_type': 'I',
                  'can': '',
                  'action': 240,
                  'id': output_to_toggle,
                  'room': 255}
        url_params = urllib.urlencode({'config': json.dumps(config)})
        self.tools._api_testee('set_input_configuration?{0}'.format(url_params), self.token)

        self.webinterface.set_output(id=output_to_toggle, is_on=True)
        self.assertTrue(self._check_if_event_is_captured(output_to_toggle, time.time(), 0), 'The Tester\'s input module should see a release after toggling the Testee\'s output. Got: {0}'.format(self.tools.input_status))
        time.sleep(0.3)
        self.webinterface.set_output(id=output_to_toggle, is_on=False)
        self.assertTrue(self._check_if_event_is_captured(output_to_toggle, time.time(), 0), 'The Tester\'s input module should keep seeing a release after toggling the Testee\'s output. Got: {0}'.format(self.tools.input_status))

    @exception_handler
    def test_toggles_all_outputs(self):
        """ Testing toggling all outputs. """
        time.sleep(0.3)
        input_number = randint(0, 7)
        config = {'name': 'togglerO',
                  'basic_actions': '173,255',
                  'invert': 255,
                  'module_type': 'I',
                  'can': '',
                  'action': 240,
                  'id': input_number,
                  'room': 255}
        url_params = urllib.urlencode({'config': json.dumps(config)})
        self.tools._api_testee('set_input_configuration?{0}'.format(url_params), self.token)

        self.webinterface.set_output(id=input_number, is_on=True)
        for i in xrange(self.INPUT_COUNT):
            self.assertTrue(self._check_if_event_is_captured(i, time.time(), 1), 'The Tester\'s input module should see a press after toggling the Testee\'s output. Got: {0}'.format(self.tools.input_status))
        time.sleep(0.3)
        self.webinterface.set_output(id=input_number, is_on=False)
        for i in xrange(self.INPUT_COUNT):
            self.assertTrue(self._check_if_event_is_captured(i, time.time(), 1), 'The Tester\'s input module should keep seeing a press since its a toggle action toggling the Testee\'s output. Got: {0}'.format(self.tools.input_status))

        time.sleep(0.3)
        self.webinterface.set_output(id=input_number, is_on=True)
        for i in xrange(self.INPUT_COUNT):
            self.assertTrue(self._check_if_event_is_captured(i, time.time(), 0), 'The Tester\'s input module should see releases after toggling the Testee\'s output. Got: {0}'.format(self.tools.input_status))

        time.sleep(0.3)
        self.webinterface.set_output(id=input_number, is_on=False)
        for i in xrange(self.INPUT_COUNT):
            self.assertTrue(self._check_if_event_is_captured(i, time.time(), 0), 'The Tester\'s input module should keep see seeing releases after toggling the Testee\'s output. Got: {0}'.format(self.tools.input_status))

    @exception_handler
    def test_turn_all_outputs_on_off(self):
        """ Testing turning all outputs on and off. """
        output_to_toggle = randint(0, 7)
        config = {'name': 'turnallO',
                  'basic_actions': '172,255',
                  'invert': 255,
                  'module_type': 'I',
                  'can': '',
                  'action': 240,
                  'id': output_to_toggle,
                  'room': 255}
        url_params = urllib.urlencode({'config': json.dumps(config)})
        self.tools._api_testee('set_input_configuration?{0}'.format(url_params), self.token)

        self.webinterface.set_output(id=output_to_toggle, is_on=True)
        for i in xrange(self.INPUT_COUNT):
            self.assertTrue(self._check_if_event_is_captured(i, time.time(), 1), 'The Tester\'s input module should see a press after toggling the Testee\'s output. Got: {0}'.format(self.tools.input_status))
        time.sleep(0.3)
        self.webinterface.set_output(id=output_to_toggle, is_on=False)
        for i in xrange(self.INPUT_COUNT):
            self.assertTrue(self._check_if_event_is_captured(i, time.time(), 1), 'The Tester\'s input module should keep seeing a press after toggling the Testee\'s output. Got: {0}'.format(self.tools.input_status))

        config = {'name': 'turnallO',
                  'basic_actions': '171,255',
                  'invert': 255,
                  'module_type': 'I',
                  'can': '',
                  'action': 240,
                  'id': output_to_toggle,
                  'room': 255}
        url_params = urllib.urlencode({'config': json.dumps(config)})
        self.tools._api_testee('set_input_configuration?{0}'.format(url_params), self.token)

        self.webinterface.set_output(id=output_to_toggle, is_on=True)
        for i in xrange(self.INPUT_COUNT):
            self.assertTrue(self._check_if_event_is_captured(i, time.time(), 0), 'The Tester\'s input module should see releases after toggling the Testee\'s output. Got: {0}'.format(self.tools.input_status))
        time.sleep(0.3)
        self.webinterface.set_output(id=output_to_toggle, is_on=False)
        for i in xrange(self.INPUT_COUNT):
            self.assertTrue(self._check_if_event_is_captured(i, time.time(), 0), 'The Tester\'s input module should keep seeing releases after toggling the Testee\'s output. Got: {0}'.format(self.tools.input_status))

    @exception_handler
    def test_toggles_all_outputs_floor(self):
        """ Testing toggling all outputs by floor number. """
        self._set_input_room_config(self.token)
        time.sleep(0.3)

        input_number = randint(0, 7)
        config = {'name': 'toggfO',
                  'basic_actions': '173,{}'.format(self.FLOOR_NUMBER),
                  'invert': 255,
                  'module_type': 'I',
                  'can': '',
                  'action': 240,
                  'id': input_number,
                  'room': 255}
        url_params = urllib.urlencode({'config': json.dumps(config)})
        self.tools._api_testee('set_input_configuration?{0}'.format(url_params), self.token)

        self.webinterface.set_output(id=input_number, is_on=True)
        for i in xrange(self.INPUT_COUNT):
            self.assertTrue(self._check_if_event_is_captured(i, time.time(), 1), 'The Tester\'s input module should see presses after toggling the Testee\'s output. Got: {0}'.format(self.tools.input_status))
        time.sleep(0.3)

        self.webinterface.set_output(id=input_number, is_on=False)
        for i in xrange(self.INPUT_COUNT):
            self.assertTrue(self._check_if_event_is_captured(i, time.time(), 1), 'The Tester\'s input module should keep seeing presses after toggling the Testee\'s output. Got: {0}'.format(self.tools.input_status))
        time.sleep(0.3)

        self.webinterface.set_output(id=input_number, is_on=True)
        for i in xrange(self.INPUT_COUNT):
            self.assertTrue(self._check_if_event_is_captured(i, time.time(), 0), 'The Tester\'s input module should see releases after toggling the Testee\'s output. Got: {0}'.format(self.tools.input_status))
        time.sleep(0.3)

        self.webinterface.set_output(id=input_number, is_on=False)
        for i in xrange(self.INPUT_COUNT):
            self.assertTrue(self._check_if_event_is_captured(i, time.time(), 0), 'The Tester\'s input module should keep seeing releases after toggling the Testee\'s output. Got: {0}'.format(self.tools.input_status))

    @exception_handler
    def test_turn_all_outputs_on_off_floor(self):
        """ Testing turning all outputs on and off by floor number. """
        self._set_input_room_config(self.token)
        time.sleep(0.3)
        input_number = randint(0, 7)
        config = {'name': 'turnerfO',
                  'basic_actions': '172,{}'.format(self.FLOOR_NUMBER),
                  'invert': 255,
                  'module_type': 'I',
                  'can': '',
                  'action': 240,
                  'id': input_number,
                  'room': 255}
        url_params = urllib.urlencode({'config': json.dumps(config)})
        self.tools._api_testee('set_input_configuration?{0}'.format(url_params), self.token)

        self.webinterface.set_output(id=input_number, is_on=True)
        for i in xrange(self.INPUT_COUNT):
            self.assertTrue(self._check_if_event_is_captured(i, time.time(), 1), 'The Tester\'s input module should see presses after toggling the Testee\'s output. Got: {0}'.format(self.tools.input_status))
        time.sleep(0.3)

        self.webinterface.set_output(id=input_number, is_on=False)
        for i in xrange(self.INPUT_COUNT):
            self.assertTrue(self._check_if_event_is_captured(i, time.time(), 1), 'The Tester\'s input module should keep seeing presses after toggling the Testee\'s output. Got: {0}'.format(self.tools.input_status))

        config = {'name': 'turnerfO',
                  'basic_actions': '171,{}'.format(self.FLOOR_NUMBER),
                  'invert': 255,
                  'module_type': 'I',
                  'can': '',
                  'action': 240,
                  'id': input_number,
                  'room': 255}
        url_params = urllib.urlencode({'config': json.dumps(config)})
        self.tools._api_testee('set_input_configuration?{0}'.format(url_params), self.token)

        self.webinterface.set_output(id=input_number, is_on=True)
        for i in xrange(self.INPUT_COUNT):
            self.assertTrue(self._check_if_event_is_captured(i, time.time(), 0), 'The Tester\'s input module should see releases after toggling the Testee\'s output. Got: {0}'.format(self.tools.input_status))
        time.sleep(0.3)

        self.webinterface.set_output(id=input_number, is_on=False)
        for i in xrange(self.INPUT_COUNT):
            self.assertTrue(self._check_if_event_is_captured(i, time.time(), 0), 'The Tester\'s input module should keep seeing releases after toggling the Testee\'s output. Got: {0}'.format(self.tools.input_status))

    @exception_handler
    def test_turn_all_outputs_off(self):
        """ Testing turning all outputs off. """
        time.sleep(0.3)

        input_number = randint(0, 7)
        config = {'name': 'turnoffO',
                  'basic_actions': '172,255',
                  'invert': 255,
                  'module_type': 'I',
                  'can': '',
                  'action': 240,
                  'id': input_number,
                  'room': 255}
        url_params = urllib.urlencode({'config': json.dumps(config)})
        self.tools._api_testee('set_input_configuration?{0}'.format(url_params), self.token)

        self.webinterface.set_output(id=input_number, is_on=True)
        for i in xrange(self.INPUT_COUNT):
            self.assertTrue(self._check_if_event_is_captured(i, time.time(), 1), 'The Tester\'s input module should see presses after toggling the Testee\'s output. Got: {0}'.format(self.tools.input_status))
        time.sleep(0.3)

        self.webinterface.set_output(id=input_number, is_on=False)
        for i in xrange(self.INPUT_COUNT):
            self.assertTrue(self._check_if_event_is_captured(i, time.time(), 1), 'The Tester\'s input module should keep seeing presses after toggling the Testee\'s output. Got: {0}'.format(self.tools.input_status))

        config = {'name': 'turnoffO',
                  'basic_actions': '164,0',
                  'invert': 255,
                  'module_type': 'I',
                  'can': '',
                  'action': 240,
                  'id': input_number,
                  'room': 255}
        url_params = urllib.urlencode({'config': json.dumps(config)})
        self.tools._api_testee('set_input_configuration?{0}'.format(url_params), self.token)

        self.webinterface.set_output(id=input_number, is_on=True)
        for i in xrange(self.INPUT_COUNT):
            self.assertTrue(self._check_if_event_is_captured(i, time.time(), 0), 'The Tester\'s input module should see releases after toggling the Testee\'s output. Got: {0}'.format(self.tools.input_status))
        time.sleep(0.3)

        self.webinterface.set_output(id=input_number, is_on=False)
        for i in xrange(self.INPUT_COUNT):
            self.assertTrue(self._check_if_event_is_captured(i, time.time(), 0), 'The Tester\'s input module should keep seeing releases after toggling the Testee\'s output. Got: {0}'.format(self.tools.input_status))

    @exception_handler
    def test_execute_group_actions_after_xtime(self):
        """ Testing the execution of a group action that will be executed after pressing an output for a while. """
        time.sleep(0.3)

        config = {'id': 1, 'actions': self.GROUP_ACTION_CONFIG.format(1), 'name': 'Test1'}
        url_params = urllib.urlencode({'config': json.dumps(config)})
        self.tools._api_testee('set_group_action_configuration?{0}'.format(url_params), self.token)

        config = {'id': 2, 'actions': self.GROUP_ACTION_CONFIG.format(2), 'name': 'Test2'}
        url_params = urllib.urlencode({'config': json.dumps(config)})
        self.tools._api_testee('set_group_action_configuration?{0}'.format(url_params), self.token)

        config = {'id': 3, 'actions': self.GROUP_ACTION_CONFIG.format(3), 'name': 'Test3'}
        url_params = urllib.urlencode({'config': json.dumps(config)})
        self.tools._api_testee('set_group_action_configuration?{0}'.format(url_params), self.token)

        config = {'id': 4, 'actions': self.GROUP_ACTION_CONFIG.format(4), 'name': 'Test4'}
        url_params = urllib.urlencode({'config': json.dumps(config)})
        self.tools._api_testee('set_group_action_configuration?{0}'.format(url_params), self.token)

        config = {'id': 5, 'actions': self.GROUP_ACTION_CONFIG.format(5), 'name': 'Test5'}
        url_params = urllib.urlencode({'config': json.dumps(config)})
        self.tools._api_testee('set_group_action_configuration?{0}'.format(url_params), self.token)

        config = {'name': 'exectime',
                  'basic_actions': '207,1,208,2,209,3,210,4,211,5',
                  'invert': 255,
                  'module_type': 'I',
                  'can': '',
                  'action': 240,
                  'id': 0,
                  'room': 255}
        url_params = urllib.urlencode({'config': json.dumps(config)})
        self.tools._api_testee('set_input_configuration?{0}'.format(url_params), self.token)

        self.webinterface.set_output(id=self.GROUP_ACTION_TARGET_ID, is_on=True)
        self.assertTrue(self._check_if_event_is_captured(1, time.time(), 1), 'The Tester\'s input module should see a press after toggling the Testee\'s output. Got: {0}'.format(self.tools.input_status))

        self.assertTrue(self._check_if_event_is_captured(2, time.time(), 1), 'The Tester\'s input module should see a press after toggling the Testee\'s output. Got: {0}'.format(self.tools.input_status))

        self.assertTrue(self._check_if_event_is_captured(3, time.time(), 1), 'The Tester\'s input module should see a press after toggling the Testee\'s output. Got: {0}'.format(self.tools.input_status))

        self.assertTrue(self._check_if_event_is_captured(4, time.time(), 1), 'The Tester\'s input module should see a press after toggling the Testee\'s output. Got: {0}'.format(self.tools.input_status))

        self.assertTrue(self._check_if_event_is_captured(5, time.time(), 1), 'The Tester\'s input module should see a press after toggling the Testee\'s output. Got: {0}'.format(self.tools.input_status))

        self.webinterface.set_output(id=self.GROUP_ACTION_TARGET_ID, is_on=False)

        self.assertTrue(self._check_if_event_is_captured(1, time.time(), 0), 'The Tester\'s input module should see a press after toggling the Testee\'s output. Got: {0}'.format(self.tools.input_status))

        self.assertTrue(self._check_if_event_is_captured(2, time.time(), 0), 'The Tester\'s input module should see a press after toggling the Testee\'s output. Got: {0}'.format(self.tools.input_status))

        self.assertTrue(self._check_if_event_is_captured(3, time.time(), 0), 'The Tester\'s input module should see a press after toggling the Testee\'s output. Got: {0}'.format(self.tools.input_status))

        self.assertTrue(self._check_if_event_is_captured(4, time.time(), 0), 'The Tester\'s input module should see a press after toggling the Testee\'s output. Got: {0}'.format(self.tools.input_status))

        self.assertTrue(self._check_if_event_is_captured(5, time.time(), 0), 'The Tester\'s input module should see a press after toggling the Testee\'s output. Got: {0}'.format(self.tools.input_status))

    @exception_handler
    def test_motion_sensor_timer_7m30s(self):
        """ Testing the setting up of a simulated motion sensor and validating the timer setting for toggling an output for 7m30s """
        i = randint(0, 7)

        modified_config = {'name': 'MotionS',
                           'basic_actions': '196,{0}'.format(i),
                           'invert': 255,
                           'module_type': 'I',
                           'can': '',
                           'action': 240,
                           'id': i,
                           'room': 255}

        url_params = urllib.urlencode({'config': json.dumps(modified_config)})
        self.tools._api_testee('set_input_configuration?{0}'.format(url_params), self.token)

        self.webinterface.set_output(id=i, is_on=True)  # Sensor detects movement
        time.sleep(0.2)
        self.webinterface.set_output(id=i, is_on=False)  # Sensor stops detecting movement

        start = time.time()
        self.assertTrue(self._check_if_event_is_captured(i, time.time(), 1), 'Should turn on an input on the Tester that act as a motion sensor.')

        time.sleep(300)
        result = self._check_if_event_is_captured(i, time.time(), 0)

        end = time.time()
        self.assertTrue(result, 'Should have unpressed the tester\'s input. Got {0}, expected output ID to untoggle: {1}'.format(result, i))
        self.assertTrue(460 > end - start > 440, 'Should toggle off after around 2m30s. Got: {0}'.format(end - start))

    @exception_handler
    def test_motion_sensor_timer_15m(self):
        """ Testing the setting up of a simulated motion sensor and validating the timer setting for toggling an output for 15m """
        i = randint(0, 7)

        modified_config = {'name': 'MotionS',
                           'basic_actions': '197,{0}'.format(i),
                           'invert': 255,
                           'module_type': 'I',
                           'can': '',
                           'action': 240,
                           'id': i,
                           'room': 255}

        url_params = urllib.urlencode({'config': json.dumps(modified_config)})
        self.tools._api_testee('set_input_configuration?{0}'.format(url_params), self.token)

        self.webinterface.set_output(id=i, is_on=True)  # Sensor detects movement
        time.sleep(0.2)
        self.webinterface.set_output(id=i, is_on=False)  # Sensor stops detecting movement

        start = time.time()
        self.assertTrue(self._check_if_event_is_captured(i, time.time(), 1), 'Should turn on an input on the Tester that act as a motion sensor.')

        time.sleep(780)
        result = self._check_if_event_is_captured(i, time.time(), 0)

        end = time.time()
        self.assertTrue(result, 'Should have unpressed the tester\'s input. Got {0}, expected output ID to untoggle: {1}'.format(result, i))
        self.assertTrue(910 > end - start > 890, 'Should toggle off after around 2m30s. Got: {0}'.format(end - start))

    @exception_handler
    def test_motion_sensor_timer_25m(self):
        """ Testing the setting up of a simulated motion sensor and validating the timer setting for toggling an output for 25m """
        i = randint(0, 7)

        modified_config = {'name': 'MotionS',
                           'basic_actions': '198,{0}'.format(i),
                           'invert': 255,
                           'module_type': 'I',
                           'can': '',
                           'action': 240,
                           'id': i,
                           'room': 255}

        url_params = urllib.urlencode({'config': json.dumps(modified_config)})
        self.tools._api_testee('set_input_configuration?{0}'.format(url_params), self.token)

        self.webinterface.set_output(id=i, is_on=True)  # Sensor detects movement
        time.sleep(0.2)
        self.webinterface.set_output(id=i, is_on=False)  # Sensor stops detecting movement

        start = time.time()

        self.assertTrue(self._check_if_event_is_captured(i, time.time(), 1), 'Should turn on an input on the Tester that act as a motion sensor.')

        time.sleep(1380)
        result = self._check_if_event_is_captured(i, time.time(), 0)

        end = time.time()
        self.assertTrue(result, 'Should have unpressed the tester\'s input. Got {0}, expected output ID to untoggle: {1}'.format(result, i))
        self.assertTrue(1510 > end - start > 1490, 'Should toggle off after around 2m30s. Got: {0}'.format(end - start))

    @exception_handler
    def test_motion_sensor_timer_37m(self):
        """ Testing the setting up of a simulated motion sensor and validating the timer setting for toggling an output for 37m """
        i = randint(0, 7)

        modified_config = {'name': 'MotionS',
                           'basic_actions': '199,{0}'.format(i),
                           'invert': 255,
                           'module_type': 'I',
                           'can': '',
                           'action': 240,
                           'id': i,
                           'room': 255}

        url_params = urllib.urlencode({'config': json.dumps(modified_config)})
        self.tools._api_testee('set_input_configuration?{0}'.format(url_params), self.token)

        self.webinterface.set_output(id=i, is_on=True)  # Sensor detects movement
        time.sleep(0.2)
        self.webinterface.set_output(id=i, is_on=False)  # Sensor stops detecting movement

        start = time.time()
        self.assertTrue(self._check_if_event_is_captured(i, time.time(), 1), 'Should turn on an input on the Tester that act as a motion sensor.')

        time.sleep(2100)
        result = self._check_if_event_is_captured(i, time.time(), 0)

        end = time.time()
        self.assertTrue(result, 'Should have unpressed the tester\'s input. Got {0}, expected output ID to untoggle: {1}'.format(result, i))
        self.assertTrue(2230 > end - start > 2210, 'Should toggle off after around 2m30s. Got: {0}'.format(end - start))

    @exception_handler
    def test_motion_sensor_timer_52m(self):
        """ Testing the setting up of a simulated motion sensor and validating the timer setting for toggling an output for 52m """
        i = randint(0, 7)

        modified_config = {'name': 'MotionS',
                           'basic_actions': '200,{0}'.format(i),
                           'invert': 255,
                           'module_type': 'I',
                           'can': '',
                           'action': 240,
                           'id': i,
                           'room': 255}

        url_params = urllib.urlencode({'config': json.dumps(modified_config)})
        self.tools._api_testee('set_input_configuration?{0}'.format(url_params), self.token)

        self.webinterface.set_output(id=i, is_on=True)  # Sensor detects movement
        time.sleep(0.2)
        self.webinterface.set_output(id=i, is_on=False)  # Sensor stops detecting movement

        start = time.time()
        self.assertTrue(self._check_if_event_is_captured(i, time.time(), 1), 'Should turn on an input on the Tester that act as a motion sensor.')

        time.sleep(3000)
        result = self._check_if_event_is_captured(i, time.time(), 0)

        end = time.time()
        self.assertTrue(result, 'Should have unpressed the tester\'s input. Got {0}, expected output ID to untoggle: {1}'.format(result, i))
        self.assertTrue(3130 > end - start > 3110, 'Should toggle off after around 2m30s. Got: {0}'.format(end - start))

    @exception_handler
    def test_time_no_overrule_2m30s(self):
        """ Testing the execution of an action (toggling output for 2m30s) without that does not overrule the timer """
        i = randint(0, 7)

        modified_output_config = {"room": 5,
                                  "can_led_4_function": "UNKNOWN",
                                  "floor": 3,
                                  "can_led_1_id": 255,
                                  "can_led_1_function": "UNKNOWN",
                                  "timer": 30,
                                  "can_led_4_id": 255,
                                  "can_led_3_id": 255,
                                  "can_led_2_function": "UNKNOWN",
                                  "id": i,
                                  "module_type": "O",
                                  "can_led_3_function": "UNKNOWN",
                                  "type": 255,
                                  "can_led_2_id": 255,
                                  "name": "Out{0}".format(i)}

        modified_input_config = {"name": "timed201",
                                 "basic_actions": "201,{0}".format(i),
                                 "invert": 255,
                                 "module_type": "I",
                                 "can": "",
                                 "action": 240,
                                 "id": i,
                                 "room": 255}

        url_params = urllib.urlencode({'config': json.dumps(modified_input_config)})
        self.tools._api_testee('set_input_configuration?{0}'.format(url_params), self.token)

        url_params = urllib.urlencode({'config': json.dumps(modified_output_config)})
        self.tools._api_testee('set_output_configuration?{0}'.format(url_params), self.token)

        self.webinterface.set_output(id=i, is_on=True)  # Sensor detects movement
        time.sleep(0.2)
        self.webinterface.set_output(id=i, is_on=False)  # Sensor stops detecting movement

        start = time.time()

        while time.time() - start < 100:
            continue
        self.assertTrue(self._check_if_event_is_captured(i, time.time(), 1), 'Should turn on an input on the Tester that act as a motion sensor.')

        self.webinterface.set_output(id=i, is_on=True)  # Sensor detects movement
        time.sleep(0.2)
        self.webinterface.set_output(id=i, is_on=False)  # Sensor stops detecting movement

        self.webinterface.set_output(id=i, is_on=True)  # Sensor detects movement
        time.sleep(0.2)
        self.webinterface.set_output(id=i, is_on=False)  # Sensor stops detecting movement

        result = self._check_if_event_is_captured(i, time.time(), 0)

        end = time.time()
        self.assertTrue(result, 'Should have unpressed the tester\'s input. Got {0}, expected output ID to untoggle: {1}'.format(result, i))
        self.assertTrue(158 > end - start > 148, 'Should still turn off after 2m30s since it first turned on. Got: {0}'.format(end - start))

    @exception_handler
    def test_time_no_overrule_7m30s(self):
        """ Testing the execution of an action (toggling output for 7m30s) without that does not overrule the timer """
        i = randint(0, 7)

        modified_output_config = {"room": 5,
                                  "can_led_4_function": "UNKNOWN",
                                  "floor": 3,
                                  "can_led_1_id": 255,
                                  "can_led_1_function": "UNKNOWN",
                                  "timer": 30,
                                  "can_led_4_id": 255,
                                  "can_led_3_id": 255,
                                  "can_led_2_function": "UNKNOWN",
                                  "id": i,
                                  "module_type": "O",
                                  "can_led_3_function": "UNKNOWN",
                                  "type": 255,
                                  "can_led_2_id": 255,
                                  "name": "Out{0}".format(i)}

        modified_input_config = {"name": "timed202",
                                 "basic_actions": "202,{0}".format(i),
                                 "invert": 255,
                                 "module_type": "I",
                                 "can": "",
                                 "action": 240,
                                 "id": i,
                                 "room": 255}

        url_params = urllib.urlencode({'config': json.dumps(modified_input_config)})
        self.tools._api_testee('set_input_configuration?{0}'.format(url_params), self.token)

        url_params = urllib.urlencode({'config': json.dumps(modified_output_config)})
        self.tools._api_testee('set_output_configuration?{0}'.format(url_params), self.token)

        self.webinterface.set_output(id=i, is_on=True)  # Sensor detects movement
        time.sleep(0.2)
        self.webinterface.set_output(id=i, is_on=False)  # Sensor stops detecting movement

        start = time.time()

        while time.time() - start < 360:
            continue
        self.assertTrue(self._check_if_event_is_captured(i, time.time(), 1), 'Should turn on an input on the Tester that act as a motion sensor.')

        self.webinterface.set_output(id=i, is_on=True)  # Sensor detects movement
        time.sleep(0.2)
        self.webinterface.set_output(id=i, is_on=False)  # Sensor stops detecting movement

        self.webinterface.set_output(id=i, is_on=True)  # Sensor detects movement
        time.sleep(0.2)
        self.webinterface.set_output(id=i, is_on=False)  # Sensor stops detecting movement

        result = self._check_if_event_is_captured(i, time.time(), 0)

        end = time.time()
        self.assertTrue(result, 'Should have unpressed the tester\'s input. Got {0}, expected output ID to untoggle: {1}'.format(result, i))
        self.assertTrue(460 > end - start > 440, 'Should still turn off after 2m30s since it first turned on. Got: {0}'.format(end - start))

    @exception_handler
    def test_time_no_overrule_15m(self):
        """ Testing the execution of an action (toggling output for 15m) without that does not overrule the timer """
        i = randint(0, 7)

        modified_output_config = {"room": 5,
                                  "can_led_4_function": "UNKNOWN",
                                  "floor": 3,
                                  "can_led_1_id": 255,
                                  "can_led_1_function": "UNKNOWN",
                                  "timer": 30,
                                  "can_led_4_id": 255,
                                  "can_led_3_id": 255,
                                  "can_led_2_function": "UNKNOWN",
                                  "id": i,
                                  "module_type": "O",
                                  "can_led_3_function": "UNKNOWN",
                                  "type": 255,
                                  "can_led_2_id": 255,
                                  "name": "Out{0}".format(i)}

        modified_input_config = {"name": "timed203",
                                 "basic_actions": "203,{0}".format(i),
                                 "invert": 255,
                                 "module_type": "I",
                                 "can": "",
                                 "action": 240,
                                 "id": i,
                                 "room": 255}

        url_params = urllib.urlencode({'config': json.dumps(modified_input_config)})
        self.tools._api_testee('set_input_configuration?{0}'.format(url_params), self.token)

        url_params = urllib.urlencode({'config': json.dumps(modified_output_config)})
        self.tools._api_testee('set_output_configuration?{0}'.format(url_params), self.token)

        self.webinterface.set_output(id=i, is_on=True)  # Sensor detects movement
        time.sleep(0.2)
        self.webinterface.set_output(id=i, is_on=False)  # Sensor stops detecting movement

        start = time.time()

        while time.time() - start < 780:
            continue
        self.assertTrue(self._check_if_event_is_captured(i, time.time(), 1), 'Should turn on an input on the Tester that act as a motion sensor.')

        self.webinterface.set_output(id=i, is_on=True)  # Sensor detects movement
        time.sleep(0.2)
        self.webinterface.set_output(id=i, is_on=False)  # Sensor stops detecting movement

        self.webinterface.set_output(id=i, is_on=True)  # Sensor detects movement
        time.sleep(0.2)
        self.webinterface.set_output(id=i, is_on=False)  # Sensor stops detecting movement

        result = self._check_if_event_is_captured(i, time.time(), 0)

        end = time.time()
        self.assertTrue(result, 'Should have unpressed the tester\'s input. Got {0}, expected output ID to untoggle: {1}'.format(result, i))
        self.assertTrue(910 > end - start > 890, 'Should still turn off after 2m30s since it first turned on. Got: {0}'.format(end - start))

    @exception_handler
    def test_time_no_overrule_25(self):
        """ Testing the execution of an action (toggling output for 25m) without that does not overrule the timer """
        i = randint(0, 7)

        modified_output_config = {"room": 5,
                                  "can_led_4_function": "UNKNOWN",
                                  "floor": 3,
                                  "can_led_1_id": 255,
                                  "can_led_1_function": "UNKNOWN",
                                  "timer": 30,
                                  "can_led_4_id": 255,
                                  "can_led_3_id": 255,
                                  "can_led_2_function": "UNKNOWN",
                                  "id": i,
                                  "module_type": "O",
                                  "can_led_3_function": "UNKNOWN",
                                  "type": 255,
                                  "can_led_2_id": 255,
                                  "name": "Out{0}".format(i+1)}

        modified_input_config = {"name": "timed204",
                                 "basic_actions": "204,{0}".format(i),
                                 "invert": 255,
                                 "module_type": "I",
                                 "can": "",
                                 "action": 240,
                                 "id": i,
                                 "room": 255}

        url_params = urllib.urlencode({'config': json.dumps(modified_input_config)})
        self.tools._api_testee('set_input_configuration?{0}'.format(url_params), self.token)

        url_params = urllib.urlencode({'config': json.dumps(modified_output_config)})
        self.tools._api_testee('set_output_configuration?{0}'.format(url_params), self.token)

        self.webinterface.set_output(id=i, is_on=True)  # Sensor detects movement
        time.sleep(0.2)
        self.webinterface.set_output(id=i, is_on=False)  # Sensor stops detecting movement

        start = time.time()

        while time.time() - start < 1380:
            continue
        self.assertTrue(self._check_if_event_is_captured(i, time.time(), 1), 'Should turn on an input on the Tester that act as a motion sensor.')

        self.webinterface.set_output(id=i, is_on=True)  # Sensor detects movement
        time.sleep(0.2)
        self.webinterface.set_output(id=i, is_on=False)  # Sensor stops detecting movement

        self.webinterface.set_output(id=i, is_on=True)  # Sensor detects movement
        time.sleep(0.2)
        self.webinterface.set_output(id=i, is_on=False)  # Sensor stops detecting movement

        result = self._check_if_event_is_captured(i, time.time(), 0)

        end = time.time()
        self.assertTrue(result, 'Should have unpressed the tester\'s input. Got {0}, expected output ID to untoggle: {1}'.format(result, i))
        self.assertTrue(1510 > end - start > 1490, 'Should still turn off after 2m30s since it first turned on. Got: {0}'.format(end - start))

    @exception_handler
    def test_time_no_overrule_37m(self):
        """ Testing the execution of an action (toggling output for 37m) without that does not overrule the timer """
        i = randint(0, 7)

        modified_output_config = {"room": 5,
                                  "can_led_4_function": "UNKNOWN",
                                  "floor": 3,
                                  "can_led_1_id": 255,
                                  "can_led_1_function": "UNKNOWN",
                                  "timer": 30,
                                  "can_led_4_id": 255,
                                  "can_led_3_id": 255,
                                  "can_led_2_function": "UNKNOWN",
                                  "id": i,
                                  "module_type": "O",
                                  "can_led_3_function": "UNKNOWN",
                                  "type": 255,
                                  "can_led_2_id": 255,
                                  "name": "Out{0}".format(i)}

        modified_input_config = {"name": "timed205",
                                 "basic_actions": "205,{0}".format(i),
                                 "invert": 255,
                                 "module_type": "I",
                                 "can": "",
                                 "action": 240,
                                 "id": i,
                                 "room": 255}

        url_params = urllib.urlencode({'config': json.dumps(modified_input_config)})
        self.tools._api_testee('set_input_configuration?{0}'.format(url_params), self.token)

        url_params = urllib.urlencode({'config': json.dumps(modified_output_config)})
        self.tools._api_testee('set_output_configuration?{0}'.format(url_params), self.token)

        self.webinterface.set_output(id=i, is_on=True)  # Sensor detects movement
        time.sleep(0.2)
        self.webinterface.set_output(id=i, is_on=False)  # Sensor stops detecting movement

        start = time.time()

        while time.time() - start < 2100:
            continue
        self.assertTrue(self._check_if_event_is_captured(i, time.time(), 1), 'Should turn on an input on the Tester that act as a motion sensor.')

        self.webinterface.set_output(id=i, is_on=True)  # Sensor detects movement
        time.sleep(0.2)
        self.webinterface.set_output(id=i, is_on=False)  # Sensor stops detecting movement

        self.webinterface.set_output(id=i, is_on=True)  # Sensor detects movement
        time.sleep(0.2)
        self.webinterface.set_output(id=i, is_on=False)  # Sensor stops detecting movement

        result = self._check_if_event_is_captured(i, time.time(), 0)

        end = time.time()
        self.assertTrue(result, 'Should have unpressed the tester\'s input. Got {0}, expected output ID to untoggle: {1}'.format(result, i))
        self.assertTrue(2230 > end - start > 2210, 'Should still turn off after 2m30s since it first turned on. Got: {0}'.format(end - start))

    @exception_handler
    def test_time_no_overrule_52m(self):
        """ Testing the execution of an action (toggling output for 52m) without that does not overrule the timer """
        i = randint(0, 7)

        modified_output_config = {"room": 5,
                                  "can_led_4_function": "UNKNOWN",
                                  "floor": 3,
                                  "can_led_1_id": 255,
                                  "can_led_1_function": "UNKNOWN",
                                  "timer": 30,
                                  "can_led_4_id": 255,
                                  "can_led_3_id": 255,
                                  "can_led_2_function": "UNKNOWN",
                                  "id": i,
                                  "module_type": "O",
                                  "can_led_3_function": "UNKNOWN",
                                  "type": 255,
                                  "can_led_2_id": 255,
                                  "name": "Out{0}".format(i)}

        modified_input_config = {"name": "timed206",
                                 "basic_actions": "206,{0}".format(i),
                                 "invert": 255,
                                 "module_type": "I",
                                 "can": "",
                                 "action": 240,
                                 "id": i,
                                 "room": 255}

        url_params = urllib.urlencode({'config': json.dumps(modified_input_config)})
        self.tools._api_testee('set_input_configuration?{0}'.format(url_params), self.token)

        url_params = urllib.urlencode({'config': json.dumps(modified_output_config)})
        self.tools._api_testee('set_output_configuration?{0}'.format(url_params), self.token)

        self.webinterface.set_output(id=i, is_on=True)  # Sensor detects movement
        time.sleep(0.2)
        self.webinterface.set_output(id=i, is_on=False)  # Sensor stops detecting movement

        start = time.time()

        while time.time() - start < 3000:
            continue
        self.assertTrue(self._check_if_event_is_captured(i, time.time(), 1), 'Should turn on an input on the Tester that act as a motion sensor.')

        self.webinterface.set_output(id=i, is_on=True)  # Sensor detects movement
        time.sleep(0.2)
        self.webinterface.set_output(id=i, is_on=False)  # Sensor stops detecting movement

        self.webinterface.set_output(id=i, is_on=True)  # Sensor detects movement
        time.sleep(0.2)
        self.webinterface.set_output(id=i, is_on=False)  # Sensor stops detecting movement

        result = self._check_if_event_is_captured(i, time.time(), 0)

        end = time.time()
        self.assertTrue(result, 'Should have unpressed the tester\'s input. Got {0}, expected output ID to untoggle: {1}'.format(result, i))
        self.assertTrue(3130 > end - start > 3110, 'Should still turn off after 2m30s since it first turned on. Got: {0}'.format(end - start))

    def _set_group_actions_config(self, token):
        """
        Sets the standard 160 group actions configurations that will toggle output id=0
        :param token: the authorization token
        :type token: str

        :return: the response from setting the group action configurations
        :rtype: request.Response

        """
        config = []
        for i in xrange(160):
            one_group_action_config = {'id': i,
                                       'actions': '240,0,244,0,240,10,161,0,235,5,160,0,235,255,240,20,160,0,235,5,161,0,235,255,240,255',
                                       'name': 'Test{0}'.format(i)}
            config.append(one_group_action_config)
        url_params = urllib.urlencode({'config': json.dumps(config)})

        return self.tools._api_testee('set_group_action_configurations?{0}'.format(url_params), token), config

    def _set_input_room_config(self, token):
        """
        Sets the standard input configuration with the relevant floor number and room number
        :param token: the authorization token
        :type token: str

        :return: the response from setting room configurations.
        :rtype: request.Response
        """
        for i in xrange(self.INPUT_COUNT):
            config = {'name': 'input'+str(i), 'basic_actions': '', 'invert': 255, 'module_type': 'I', 'can': '',
                      'action': i, 'id': i, 'room': self.ROOM_NUMBER}
            url_params = urllib.urlencode({'config': json.dumps(config)})
            self.tools._api_testee('set_input_configuration?{0}'.format(url_params), self.token)

        config = []
        for i in xrange(100):
            one_room_config = {'id': i, 'name': 'room{}'.format(self.ROOM_NUMBER), 'floor': self.FLOOR_NUMBER}
            config.append(one_room_config)
        url_params = urllib.urlencode({'config': json.dumps(config)})

        return self.tools._api_testee('set_room_configurations?{0}'.format(url_params), token)

    def _check_if_event_is_captured(self, toggled_output, start, value):
        """
        Checks if the toggled output has turned an input on.
        :param toggled_output: the id of the toggled output
        :type toggled_output: int

        :param start: the time from which counting will start
        :type start: float

        :param value: the expected is_on value of the input.
        :type value: int

        :return: if the the toggled output has turned an input on
        :rtype: bool
        """
        while self.tools.input_status.get(str(toggled_output)) is not str(value):
            if time.time() - start < self.tools.TIMEOUT:
                time.sleep(0.3)
                continue
            return False
        return True
