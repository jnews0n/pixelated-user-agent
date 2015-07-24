#
# Copyright (c) 2015 ThoughtWorks, Inc.
#
# Pixelated is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Pixelated is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with Pixelated. If not, see <http://www.gnu.org/licenses/>.
import json
from uuid import uuid4
from email.parser import Parser
import os
from leap.soledad.common.document import SoledadDocument

from twisted.internet.defer import FirstError
from twisted.trial.unittest import TestCase
from leap.mail import constants
from twisted.internet import defer
from mockito import mock, when, verify, any
from leap.mail.adaptors.soledad import SoledadMailAdaptor
import pkg_resources
from leap.mail.mail import Message

from pixelated.adapter.mailstore.leap_mailstore import LeapMailStore, LeapMail


class TestLeapMail(TestCase):
    def test_leap_mail(self):
        mail = LeapMail('', {'From': 'test@example.test', 'Subject': 'A test Mail', 'To': 'receiver@example.test'})

        self.assertEqual('test@example.test', mail.from_sender)
        self.assertEqual('receiver@example.test', mail.to)
        self.assertEqual('A test Mail', mail.subject)

    def test_as_dict(self):
        mail = LeapMail('doc id', {'From': 'test@example.test', 'Subject': 'A test Mail', 'To': 'receiver@example.test'}, ('foo', 'bar'))

        expected = {
            'header': {
                'from': 'test@example.test',
                'subject': 'A test Mail',
                'to': 'receiver@example.test',

            },
            'ident': 'doc id',
            'tags': ('foo', 'bar'),
            'body': None
        }

        self.assertEqual(expected, mail.as_dict())

    def test_as_dict_with_body(self):
        body = 'some body content'
        mail = LeapMail('doc id', {'From': 'test@example.test', 'Subject': 'A test Mail', 'To': 'receiver@example.test'}, ('foo', 'bar'), body=body)

        self.assertEqual(body, mail.as_dict()['body'])


class TestLeapMailStore(TestCase):
    def setUp(self):
        self.soledad = mock()
        self.mbox_uuid = str(uuid4())
        self.doc_by_id = {}

    @defer.inlineCallbacks
    def test_get_mail_not_exist(self):
        store = LeapMailStore(self.soledad)

        mail = yield store.get_mail(_format_mdoc_id(uuid4(), 1))

        self.assertIsNone(mail)

    @defer.inlineCallbacks
    def test_get_mail(self):
        mdoc_id, _ = self._add_mail_fixture_to_soledad('mbox00000000')

        store = LeapMailStore(self.soledad)

        mail = yield store.get_mail(mdoc_id)

        self.assertIsInstance(mail, LeapMail)
        self.assertEqual('darby.senger@zemlak.biz', mail.from_sender)
        self.assertEqual('carmel@murazikortiz.name', mail.to)
        self.assertEqual('Itaque consequatur repellendus provident sunt quia.', mail.subject)
        self.assertIsNone(mail.body)

    @defer.inlineCallbacks
    def test_get_two_different_mails(self):
        first_mdoc_id, _ = self._add_mail_fixture_to_soledad('mbox00000000')
        second_mdoc_id, _ = self._add_mail_fixture_to_soledad('mbox00000001')

        store = LeapMailStore(self.soledad)

        mail1 = yield store.get_mail(first_mdoc_id)
        mail2 = yield store.get_mail(second_mdoc_id)

        self.assertNotEqual(mail1, mail2)
        self.assertEqual('Itaque consequatur repellendus provident sunt quia.', mail1.subject)
        self.assertEqual('Error illum dignissimos autem eos aspernatur.', mail2.subject)

    @defer.inlineCallbacks
    def test_get_mails(self):
        first_mdoc_id, _ = self._add_mail_fixture_to_soledad('mbox00000000')
        second_mdoc_id, _ = self._add_mail_fixture_to_soledad('mbox00000001')

        store = LeapMailStore(self.soledad)

        mails = yield store.get_mails([first_mdoc_id, second_mdoc_id])

        self.assertEqual(2, len(mails))
        self.assertEqual('Itaque consequatur repellendus provident sunt quia.', mails[0].subject)
        self.assertEqual('Error illum dignissimos autem eos aspernatur.', mails[1].subject)

    @defer.inlineCallbacks
    def test_get_mails_fails_for_invalid_mail_id(self):
        store = LeapMailStore(self.soledad)

        try:
            yield store.get_mails(['invalid'])
            self.fail('Exception expected')
        except FirstError:
            pass

    @defer.inlineCallbacks
    def test_get_mail_with_body(self):
        expeted_body = 'Dignissimos ducimus veritatis. Est tenetur consequatur quia occaecati. Vel sit sit voluptas.\n\nEarum distinctio eos. Accusantium qui sint ut quia assumenda. Facere dignissimos inventore autem sit amet. Pariatur voluptatem sint est.\n\nUt recusandae praesentium aspernatur. Exercitationem amet placeat deserunt quae consequatur eum. Unde doloremque suscipit quia.\n\n'
        mdoc_id, _ = self._add_mail_fixture_to_soledad('mbox00000000')

        store = LeapMailStore(self.soledad)

        mail = yield store.get_mail(mdoc_id, include_body=True)

        self.assertEqual(expeted_body, mail.body)

    @defer.inlineCallbacks
    def test_update_mail(self):
        mdoc_id, fdoc_id = self._add_mail_fixture_to_soledad('mbox00000000')
        soledad_fdoc = self.doc_by_id[fdoc_id]
        when(self.soledad).put_doc(soledad_fdoc).thenReturn(defer.succeed(None))

        store = LeapMailStore(self.soledad)

        mail = yield store.get_mail(mdoc_id)

        mail.tags.add('new_tag')

        yield store.update_mail(mail)

        verify(self.soledad).put_doc(soledad_fdoc)
        self.assertTrue('new_tag' in soledad_fdoc.content['tags'])

    def _add_mail_fixture_to_soledad(self, mail_file):
        mail = self._load_mail_from_file(mail_file)
        msg = self._convert_mail_to_leap_message(mail)
        wrapper = msg.get_wrapper()

        mdoc_id = wrapper.mdoc.future_doc_id
        fdoc_id = wrapper.mdoc.fdoc
        hdoc_id = wrapper.mdoc.hdoc
        cdoc_id = wrapper.mdoc.cdocs[0]

        self._mock_soledad_doc(mdoc_id, wrapper.mdoc)
        self._mock_soledad_doc(fdoc_id, wrapper.fdoc)
        self._mock_soledad_doc(hdoc_id, wrapper.hdoc)
        self._mock_soledad_doc(cdoc_id, wrapper.cdocs[1])

        return mdoc_id, fdoc_id

    def _convert_mail_to_leap_message(self, mail):
        msg = SoledadMailAdaptor().get_msg_from_string(Message, mail.as_string())
        msg.get_wrapper().mdoc.set_mbox_uuid(self.mbox_uuid)
        return msg

    def _mock_soledad_doc(self, doc_id, doc):
        soledad_doc = SoledadDocument(doc_id, json=json.dumps(doc.serialize()))

        when(self.soledad).get_doc(doc_id).thenReturn(defer.succeed(soledad_doc))

        self.doc_by_id[doc_id] = soledad_doc

    def _load_mail_from_file(self, mail_file):
        mailset_dir = pkg_resources.resource_filename('test.unit.fixtures', 'mailset')
        mail_file = os.path.join(mailset_dir, 'new', mail_file)
        with open(mail_file) as f:
            mail = Parser().parse(f)
        return mail


def _format_mdoc_id(mbox_uuid, chash):
    return constants.METAMSGID.format(mbox_uuid=mbox_uuid, chash=chash)