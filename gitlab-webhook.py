#!/usr/bin/env python2.6

import os
import json
import BaseHTTPServer
import shlex
import subprocess
import shutil
import logging
import ConfigParser

logger = logging.getLogger('gitlab-webhook-processor')
logger.setLevel(logging.DEBUG)
logging_handler = logging.StreamHandler()
logging_handler.setFormatter(
	logging.Formatter("%(asctime)s %(levelname)s %(message)s",
					  "%B %d %H:%M:%S"))
logger.addHandler(logging_handler)

config = ConfigParser.RawConfigParser()
config.read('gitlab-webhook.ini')

class RequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):
	branch_dir = ''
	repository = ''

	def do_POST(self):
		logger.info("Received POST request.")
		self.rfile._sock.settimeout(5)
		
		if not self.headers.has_key('Content-Length'):
			return self.error_response()
		
		json_data = self.rfile.read(
			int(self.headers['Content-Length'])).decode('utf-8')

		try:
			data = json.loads(json_data)
		except ValueError:
			logger.error("Unable to load JSON data '%s'" % json_data)
			return self.error_response()

		data_repository = data.get('repository', {}).get('url')
		
		if len(self.path) > 1:
			config_name = self.path[1:]
			if config.has_section(config_name):
				self.branch_dir = config.get(config_name, 'BranchDir')
				self.repository = config.get(config_name, 'Repository')
				config_branch_name = config.get(config_name, 'BranchName')
				
				if data_repository == self.repository:
					branch_to_update = data.get('ref', '').split('refs/heads/')[-1]
					branch_to_update = branch_to_update.replace('; ', '')
					if branch_to_update == '':
						logger.error("Unable to identify branch to update: '%s'" %
									 data.get('ref', ''))
						return self.error_response()
					elif (branch_to_update.find("/") != -1 or
						  branch_to_update in ['.', '..']):
						# Avoid feature branches, malicious branches and similar.
						logger.debug("Skipping update for branch '%s'." %
									 branch_to_update)
					else:
						if branch_to_update == config_branch_name:
							self.ok_response()
							branch_deletion = data['after'].replace('0', '') == ''
							branch_addition = data['before'].replace('0', '') == ''
							if branch_addition:
								self.add_branch(branch_to_update)
							elif branch_deletion:
								self.remove_branch(branch_to_update)
							else:
								self.update_branch(branch_to_update)
							return 
						else:
							logger.debug(("Branch '%s' is not our branch '%s'. "
										  "Ignoring.") % (branch_to_update, config_branch_name))
				else:
					logger.debug(("Repository '%s' is not our repository '%s'. "
								  "Ignoring.") % (data_repository, self.repository))
			else:
				logger.debug(("There is no config with name '%s'. "
							  "Ignoring.") % (config_name))
		else:
			logger.info("Empty config name!")
			

		self.ok_response()
		logger.info("Finished processing POST request.")

	def add_branch(self, branch):
		os.chdir(self.branch_dir)
		branch_path = self.branch_dir
		if os.path.isdir(branch_path):
			return self.update_branch(branch_path)
		run_command(r"/usr/bin/git clone --depth 1 -o origin -b %s %s %s" %
					(branch, self.repository, branch))
		os.chmod(branch_path, 0770)
		logger.info("Added directory '%s'" % branch_path)

	def update_branch(self, branch):
		branch_path = self.branch_dir
		if not os.path.isdir(branch_path):
			return self.add_branch(branch)
		os.chdir(branch_path)
		run_command(r"/usr/bin/git checkout -f %s" % branch)
		run_command(r"/usr/bin/git clean -fdx")
		run_command(r"/usr/bin/git fetch origin %s" % branch)
		run_command(r"/usr/bin/git reset --hard FETCH_HEAD")
		logger.info("Updated branch '%s'" % branch_path)
		
	def remove_branch(self, branch):
		branch_path = self.branch_dir
		if not os.path.isdir(branch_path):
			logger.warn("Directory to remove does not exist: %s" % branch_path)
			return
		try:
			shutil.rmtree(branch_path)
		except (OSError, IOError), e:
			logger.exception("Error removing directory '%s'" % branch_path)
		else:
			logger.info("Removed directory '%s'" % branch_path)
		
	def ok_response(self):
		self.send_response(200)
		self.send_header("Content-type", "text/plain")
		self.end_headers()

	def error_response(self):
		self.log_error("Bad Request.")
		self.send_response(400)
		self.send_header("Content-type", "text/plain")
		self.end_headers()
		

def run_command(command):
	logger.debug("Running command: %s" % command)
	os.system(command)
		
def main():
	host, port = config.get('SYSTEM_CONFIGURATION', 'WebhookHost'), int(config.get('SYSTEM_CONFIGURATION', 'WebhookPort'))
	
	server = BaseHTTPServer.HTTPServer((host, port), RequestHandler)
	logger.info("Starting HTTP Server at %s:%s." % (host, port))

	try:
		server.serve_forever()
	except KeyboardInterrupt:
		pass
	logger.info("Stopping HTTP Server.")
	server.server_close()
	
if __name__ == '__main__':
	main()
