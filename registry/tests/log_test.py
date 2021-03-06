# Copyright (c) 2017 Quilt Data, Inc. All rights reserved.

"""
Log tests
"""

import json
import requests
from unittest.mock import patch

from quilt_server.const import PaymentPlan, PUBLIC
from quilt_server.core import hash_contents, GroupNode, RootNode
from .utils import QuiltTestCase


class LogTestCase(QuiltTestCase):
    """
    Test log endpoint.
    """
    def setUp(self):
        super(LogTestCase, self).setUp()

        self.user = "test_user"
        self.pkg = "pkg"
        self.contents_list = [
            RootNode(dict(
                foo=GroupNode(dict())
            )),
            RootNode(dict(
                bar=GroupNode(dict())
            )),
            RootNode(dict(
                baz=GroupNode(dict())
            ))
        ]

        # Upload three package instances.
        for contents in self.contents_list:
            self.put_package(self.user, self.pkg, contents, tag_latest=True)

        def make_version(i, version):
            resp = self.app.put(
                '/api/version/{usr}/{pkg}/{version}'.format(
                    usr=self.user,
                    pkg=self.pkg,
                    version=version
                ),
                data=json.dumps(dict(
                    hash=hash_contents(self.contents_list[i])
                )),
                content_type='application/json',
                headers={
                    'Authorization': self.user
                }
            )
            assert resp.status_code == requests.codes.ok

        make_version(0, '1.0.0')
        make_version(1, '2.0.0')
        make_version(2, '3.0.0')


    def testLog(self):
        resp = self.app.get(
            '/api/log/{usr}/{pkg}/'.format(
                usr=self.user,
                pkg=self.pkg
            ),
            headers={
                'Authorization': self.user
            }
        )
        assert resp.status_code == requests.codes.ok

        data = json.loads(resp.data.decode('utf8'))
        logs = data['logs']

        assert len(logs) == 3

        tag_list = [None, None, ['latest']]
        version_list = [['1.0.0'], ['2.0.0'], ['3.0.0']]
        for log, contents, tags, versions in zip(logs, self.contents_list, tag_list, version_list):
            assert log['author'] == self.user
            assert log['hash'] == hash_contents(contents)
            assert log['tags'] == tags
            assert log['versions'] == versions

    @patch('quilt_server.views.ALLOW_ANONYMOUS_ACCESS', True)
    def testAccess(self):
        sharewith = "share_with"

        # Can't view as a user with no access.
        resp = self.app.get(
            '/api/log/{usr}/{pkg}/'.format(
                usr=self.user,
                pkg=self.pkg
            ),
            headers={
                'Authorization': sharewith
            }
        )
        assert resp.status_code == requests.codes.not_found

        # Can't view when not logged in.
        resp = self.app.get(
            '/api/log/{usr}/{pkg}/'.format(
                usr=self.user,
                pkg=self.pkg
            ),
        )
        assert resp.status_code == requests.codes.not_found

        # Share the package.
        resp = self._share_package(self.user, self.pkg, sharewith)
        assert resp.status_code == requests.codes.ok

        # Can view once it's shared.
        resp = self.app.get(
            '/api/log/{usr}/{pkg}/'.format(
                usr=self.user,
                pkg=self.pkg
            ),
            headers={
                'Authorization': sharewith
            }
        )
        assert resp.status_code == requests.codes.ok

        # Still can't view when not logged in.
        resp = self.app.get(
            '/api/log/{usr}/{pkg}/'.format(
                usr=self.user,
                pkg=self.pkg
            ),
        )
        assert resp.status_code == requests.codes.not_found

        # Share the package publicly.
        resp = self._share_package(self.user, self.pkg, PUBLIC)
        assert resp.status_code == requests.codes.ok

        # Can now view when not logged in.
        resp = self.app.get(
            '/api/log/{usr}/{pkg}/'.format(
                usr=self.user,
                pkg=self.pkg
            ),
        )
        assert resp.status_code == requests.codes.ok
