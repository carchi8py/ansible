# (c) 2019, NetApp, Inc
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

''' unit tests for Ansible module: na_ontap_volume_autosize '''

from __future__ import print_function
import json
import pytest

from units.compat import unittest
from units.compat.mock import patch, Mock
from ansible.module_utils import basic
from ansible.module_utils._text import to_bytes
import ansible.module_utils.netapp as netapp_utils

from ansible.modules.storage.netapp.na_ontap_volume_autosize \
    import NetAppOntapVolumeAutosize as autosize_module  # module under test

if not netapp_utils.has_netapp_lib():
    pytestmark = pytest.mark.skip('skipping as missing required netapp_lib')


def set_module_args(args):
    """prepare arguments so that they will be picked up during module creation"""
    args = json.dumps({'ANSIBLE_MODULE_ARGS': args})
    basic._ANSIBLE_ARGS = to_bytes(args)  # pylint: disable=protected-access


class AnsibleExitJson(Exception):
    """Exception class to be raised by module.exit_json and caught by the test case"""
    pass


class AnsibleFailJson(Exception):
    """Exception class to be raised by module.fail_json and caught by the test case"""
    pass


def exit_json(*args, **kwargs):  # pylint: disable=unused-argument
    """function to patch over exit_json; package return data into an exception"""
    if 'changed' not in kwargs:
        kwargs['changed'] = False
    raise AnsibleExitJson(kwargs)


def fail_json(*args, **kwargs):  # pylint: disable=unused-argument
    """function to patch over fail_json; package return data into an exception"""
    kwargs['failed'] = True
    raise AnsibleFailJson(kwargs)


class MockONTAPConnection(object):
    ''' mock server connection to ONTAP host '''

    def __init__(self, kind=None, data=None):
        ''' save arguments '''
        self.kind = kind
        self.params = data
        self.xml_in = None
        self.xml_out = None

    def invoke_successfully(self, xml, enable_tunneling):  # pylint: disable=unused-argument
        ''' mock invoke_successfully returning xml data '''
        self.xml_in = xml
        if self.kind == 'autosize':
            xml = self.build_autosize_info(self.params)
        self.xml_out = xml
        return xml

    @staticmethod
    def build_autosize_info(autosize_details):
        xml = netapp_utils.zapi.NaElement('xml')
        attributes = {
            'grow-threshold-percent': autosize_details['grow_threshold_percent'],
            'maximum-size': '10485760',
            'minimum-size': '21504',
            'increment_size': '10240',
            'mode': autosize_details['mode'],
            'shrink-threshold-percent': autosize_details['shrink_threshold_percent']
        }
        xml.translate_struct(attributes)
        return xml


class TestMyModule(unittest.TestCase):
    ''' Unit tests for na_ontap_job_schedule '''

    def setUp(self):
        self.mock_module_helper = patch.multiple(basic.AnsibleModule,
                                                 exit_json=exit_json,
                                                 fail_json=fail_json)
        self.mock_module_helper.start()
        self.addCleanup(self.mock_module_helper.stop)
        self.mock_autosize = {
            'grow_threshold_percent': 99,
            'maximum_size': '10g',
            'minimum_size': '21m',
            'increment_size': '10m',
            'mode': 'grow',
            'shrink_threshold_percent': 40,
            'vserver': 'test_vserver',
            'volume': 'test_volume'
        }

    def mock_args(self):
        return {
            'vserver': self.mock_autosize['vserver'],
            'volume': self.mock_autosize['volume'],
            'grow_threshold_percent': self.mock_autosize['grow_threshold_percent'],
            'maximum_size': self.mock_autosize['maximum_size'],
            'minimum_size': self.mock_autosize['minimum_size'],
            'increment_size': self.mock_autosize['increment_size'],
            'mode': self.mock_autosize['mode'],
            'shrink_threshold_percent': self.mock_autosize['shrink_threshold_percent'],
            'hostname': 'test',
            'username': 'test_user',
            'password': 'test_pass!'
        }

    def get_autosize_mock_object(self, kind=None):
        autosize_obj = autosize_module()
        if kind is None:
            autosize_obj.server = MockONTAPConnection()
        elif kind is 'autosize':
            autosize_obj.server = MockONTAPConnection(kind='autosize', data=self.mock_autosize)
        return autosize_obj

    def test_module_fail_when_required_args_missing(self):
        ''' required arguments are reported as errors '''
        with pytest.raises(AnsibleFailJson) as exc:
            set_module_args({})
            autosize_module()
        print('Info: %s' % exc.value.args[0]['msg'])

    def test_idempotent_modify(self):
        set_module_args(self.mock_args())
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_autosize_mock_object('autosize').apply()
        assert not exc.value.args[0]['changed']

    def test_successful_modify(self):
        data = self.mock_args()
        data['maximum_size'] = '11g'
        set_module_args(data)
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_autosize_mock_object('autosize').apply()
        assert exc.value.args[0]['changed']

    def test_successful_reset(self):
        data = {}
        data['reset'] = True
        data['hostname'] = 'test'
        data['username'] = 'test_user'
        data['password'] = 'test_pass!'
        data['volume'] = 'test_vol'
        data['vserver'] = 'test_vserver'
        set_module_args(data)
        with pytest.raises(AnsibleExitJson) as exc:
            self.get_autosize_mock_object('autosize').apply()
        assert exc.value.args[0]['changed']
