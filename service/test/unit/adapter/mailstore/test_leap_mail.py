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
from twisted.trial.unittest import TestCase

from pixelated.adapter.mailstore.leap_mailstore import LeapMail, AttachmentInfo


class TestLeapMail(TestCase):
    def test_leap_mail(self):
        mail = LeapMail('', 'INBOX', {'From': 'test@example.test', 'Subject': 'A test Mail', 'To': 'receiver@example.test'})

        self.assertEqual('test@example.test', mail.from_sender)
        self.assertEqual(['receiver@example.test'], mail.to)
        self.assertEqual('A test Mail', mail.subject)

    def test_email_addresses_in_to_are_split_into_a_list(self):
        mail = LeapMail('', 'INBOX', {'To': 'first@example.test,second@example.test'})

        self.assertEqual(['first@example.test', 'second@example.test'], mail.headers['To'])

    def test_email_addresses_in_cc_are_split_into_a_list(self):
        mail = LeapMail('', 'INBOX', {'Cc': 'first@example.test,second@example.test'})

        self.assertEqual(['first@example.test', 'second@example.test'], mail.headers['Cc'])

    def test_email_addresses_in_bcc_are_split_into_a_list(self):
        mail = LeapMail('', 'INBOX', {'Bcc': 'first@example.test,second@example.test'})

        self.assertEqual(['first@example.test', 'second@example.test'], mail.headers['Bcc'])

    def test_email_addresses_might_be_empty_array(self):
        mail = LeapMail('', 'INBOX', {'Cc': None})

        self.assertEqual([], mail.headers['Cc'])

    def test_as_dict(self):
        mail = LeapMail('doc id', 'INBOX', {'From': 'test@example.test', 'Subject': 'A test Mail', 'To': 'receiver@example.test,receiver2@other.test'}, ('foo', 'bar'))

        expected = {
            'header': {
                'from': 'test@example.test',
                'subject': 'A test Mail',
                'to': ['receiver@example.test', 'receiver2@other.test'],

            },
            'ident': 'doc id',
            'mailbox': 'inbox',
            'tags': {'foo', 'bar'},
            'status': [],
            'body': None,
            'textPlainBody': None,
            'replying': {'all': {'cc-field': [],
                                 'to-field': ['receiver@example.test',
                                              'receiver2@other.test',
                                              'test@example.test']},
                         'single': 'test@example.test'},
            'attachments': []
        }

        self.assertEqual(expected, mail.as_dict())

    def test_as_dict_with_body(self):
        body = 'some body content'
        mail = LeapMail('doc id', 'INBOX', {'From': 'test@example.test', 'Subject': 'A test Mail', 'To': 'receiver@example.test'}, ('foo', 'bar'), body=body)

        self.assertEqual(body, mail.as_dict()['body'])

    def test_as_dict_with_attachments(self):
        mail = LeapMail('doc id', 'INBOX', attachments=[AttachmentInfo('id', 'name', 'encoding')])

        self.assertEqual([{'ident': 'id', 'name': 'name', 'encoding': 'encoding'}],
                         mail.as_dict()['attachments'])

    def test_raw_constructed_by_headers_and_body(self):
        body = 'some body content'
        mail = LeapMail('doc id', 'INBOX', {'From': 'test@example.test', 'Subject': 'A test Mail', 'To': 'receiver@example.test'}, ('foo', 'bar'), body=body)

        result = mail.raw

        expected_raw = 'To: receiver@example.test\nFrom: test@example.test\nSubject: A test Mail\n\nsome body content'
        self.assertEqual(expected_raw, result)

    def test_headers_none_recipients_are_converted_to_empty_array(self):
        mail = LeapMail('id', 'INBOX', {'To': None, 'Cc': None, 'Bcc': None})

        self.assertEquals([], mail.headers['To'])
        self.assertEquals([], mail.headers['Cc'])
        self.assertEquals([], mail.headers['Bcc'])