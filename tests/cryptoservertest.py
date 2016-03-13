#encoding: utf-8
import unittest
from server import CryptoServerBase

class Bunch:
    def __init__(self, **kwds):
        self.__dict__.update(kwds)

class FakeSyslog(object):
    def __init__(self):
        self.logged = ""
    def syslog(self, msg):
        self.logged += msg
    def openlog(self,*args, **kwargs):
        self.logged += "openlog:{0} {1}".format(args, kwargs)

class FakeRequest(object):
    def __init__(self,msg):
        self.msg = msg
    def recv(self, length):
        return self.msg
    
    def sendall(self, msg):
        self.sent=msg

class CryproServerTest(unittest.TestCase):

    def setUp(self):
        self.fixture = CryptoServerBase()
        self.fixture.syslog = FakeSyslog()

        self.fixture.opts = Bunch(
            module="/usr/lib/softhsm/libsofthsm.so",
            pin="0000",
            keyid="d34db33f",
            mechanism="SHA512-RSA-PKCS",
            verbose=False,
            inputlength=512,
            outputlength=256,
            )
        self.fixture.request = FakeRequest("a"*512)

    def prepareFakeOutput(self, length):
        name = self.fixture.getTempName()
        f = open(name, "w")
        f.write("a" * length)
        f.close()
        return name

    def test_getTempName_returns_a_filename_which_can_be_created(self):
        name = self.fixture.getTempName()
        self.assertEqual(file, open(name,"w").__class__)

    def test_commandLine_is_compiled_properly(self):
        commandLine = self.fixture.compileCommandLine("theName")
        self.assertEqual([
                'pkcs11-tool',
                '--module', '/usr/lib/softhsm/libsofthsm.so',
                '-l',
                '-p', '0000',
                '-d', 'd34db33f',
                '-m', 'SHA512-RSA-PKCS',
                '-s',
                '-o', 'theName'
            ], commandLine)

    def test_runCommand_throws_exception_if_command_fails(self):
        with self.assertRaises(RuntimeError):
            self.fixture.runCommand("", ["/bin/false"])
            
    def test_runCommand_logs_stdout(self):
        self.fixture.runCommand("hello world", ["cat"])
        self.assertEqual("hello world",self.fixture.syslog.logged)

    def test_runCommand_logs_stderr(self):
        self.fixture.runCommand("hello world", ["dd", "of=/dev/null"])
        self.assertTrue(
            self.fixture.syslog.logged.startswith(
                '0+1 records in\n0+1 records out\n11 bytes (11 B) copied,'))

    def test_runCommand_logs_catches_errors(self):
        with self.assertRaises(RuntimeError):
            self.fixture.runCommand("hello world", ["ajj"])
        self.assertEqual('problem running command: [Errno 2] No such file or directory',self.fixture.syslog.logged)

    def test_input_length_is_checked(self):
        self.fixture.request = FakeRequest("a"*511)
        with self.assertRaises(RuntimeError):
            self.fixture.receiveData()
        self.assertEqual('input is not 512 bytes (511 bytes)',self.fixture.syslog.logged)

    def test_good_input_length_is_accepted(self):
        result = self.fixture.receiveData()
        self.assertEqual("a"*512,result)

    def test_output_length_is_checked(self):
        name = self.prepareFakeOutput(511)
        with self.assertRaises(RuntimeError):
            self.fixture.getResponse(name)
        self.assertEqual('command output is not 256 bytes (511 bytes)',self.fixture.syslog.logged)

    def test_good_output_length_is_accepted(self):
        name = self.prepareFakeOutput(256)
        result = self.fixture.getResponse(name)
        self.assertEqual("a"*256,result)

    def test_handle_plays_it_all(self):
        self.fixture.handle()
        self.assertEqual('"\xdb$Y<{Yxe~\xb7(\x14\xd5V*\x91\xef\xeek\x9b\xc5\x9d\xcc\x04<G\x1cu\x08s\t\x9c\x05Rt\xf4\x15\xf6\x8bi\x9cW\x0c[\xaa#\xfa\xc3\xf7\x04\x19\x8c{F\x83\x9d\x14\xa2w\tla*\x8bJ\x17\xd2\x04 \xfd\x07\xe8\x1b\xed\xfd\x9dY\x96\xa1`6\'+\xc5,\x9b\x02\x1bZ\xad\xd5\x0b\xca4\xecdcL\xa0Y\x0b\xabz ?\x0e\xf1\xef\xa1\xd3Q\xcd\xa7\x1eg%\xe2B\xd8].\x14\x1c\';\xc6\xd3\x07\xd0\r\x14\xc2\xdd[\xeb}\xeb\x8f\x97Hp|\x0e\xaf\xf6\xa2\x05\x0c8 \x034\xa6\xe8\x106NHD\xa9\x8f\xb8i~@h\xc3\xefT\x7f\x05\x1d\xd4W\x92\x92\xfb\xd34\xe8\x984\xe4\xbf\xed3\x82\xf2y(\x0fo\xb3Q\xb9\xa9\xb8NR\xa3\x94(e\xcf\xa3\x18\x06\x93\xba\xf2\xba\xda\xed$\xda\xb0\xb3\x95#\xf3\xbdZ\xf2\xc1\x13\xae\xf77\xd2\xd8\xa3\x0f`\x94u\x8a\xf0\xd3\xe4!s\xa0\xc9\x9d#\xed\xb8\xdf\xd8S\x82\x8c\x0c\x0bb',
                         self.fixture.request.sent)

    def test_problems_result_in_error_message(self):
        self.fixture.request = FakeRequest("a"*511)
        self.fixture.handle()
        self.assertEqual("an error occured, try again later", self.fixture.request.sent)

    def test_problems_are_logged(self):
        self.fixture.request = FakeRequest("a"*511)
        self.fixture.handle()
        self.assertEqual("input is not 512 bytes (511 bytes)", self.fixture.syslog.logged)