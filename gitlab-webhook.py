#!/usr/bin/env python

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
config.read('%s/gitlab-webhook.ini' % os.path.dirname(os.path.abspath(__file__)))
gitlab_ip = config.get('SYSTEM_CONFIGURATION', 'GitlabIP')
rails_path = config.get('SYSTEM_CONFIGURATION', 'RailsPath')

class RequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):
	section = None

	def do_POST(self):
		logger.info("Received POST request.")
		
		self.rfile._sock.settimeout(5)
		
		if self.client_address[0] != gitlab_ip:
			logger.info("Wrong request source IP!")
			return self.error_response()
		
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
				self.section = dict(config.items(config_name))
				
				if data_repository == self.section['repository'] and self.section.has_key('branchname'):
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
						if branch_to_update == self.section['branchname']:
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
										  "Ignoring.") % (branch_to_update, self.section['branchname']))
				else:
					logger.debug(("Repository '%s' is not our repository '%s'. "
								  "Ignoring.") % (data_repository, self.section['repository']))
			else:
				logger.debug(("There is no config with name '%s'. "
							  "Ignoring.") % (config_name))
		else:
			logger.info("Empty config name!")
			

		self.ok_response()
		logger.info("Finished processing POST request.")

	def add_branch(self, branch):
		if not self.section.has_key('branchdir'):
			return
		branch_path = self.section['branchdir']

		os.chdir(branch_path)

		if os.path.isdir(branch_path):
			return self.update_branch(branch_path)
		run_command(r"/usr/bin/git clone --depth 1 -o origin -b %s %s %s" %
					(branch, self.section['repository'], branch))
		os.chmod(branch_path, 0770)
		logger.info("Added directory '%s'" % branch_path)

	def update_branch(self, branch):
		if not self.section.has_key('branchdir'):
			return
		branch_path = self.section['branchdir']

		if not os.path.isdir(branch_path):
			return self.add_branch(branch)
		os.chdir(branch_path)
		
		# Run bash script before doing pull
		if self.section.has_key('shbefore'):
			run_command(self.section['shbefore'], True)

		# git pull!
 		run_command(r"/usr/bin/git pull origin %(branch)s" % {'branch': branch})

		# Run bash script after doing pull
		if self.section.has_key('shafter'):
			run_command(self.section['shafter'], True)

		# Updating redmine storage
 		if rails_path != "false" and self.section.has_key('projectid') and self.section['projectid'] != "false":
			run_command(""" %(rails_path)s runner "Project.find_by_identifier('%(project)s').try(:repository).try(:fetch_changesets)" -e production """ %
					{'project': self.section['projectid'], 'rails_path' : rails_path})
 					
		logger.info("Updated branch '%s'" % branch_path)
		
	def remove_branch(self, branch):
		if not self.section.has_key('branchdir'):
			return
		branch_path = self.section['branchdir']

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
		

def run_command(command, detached=False):
	logger.debug("Running command: %s" % command)
	if detached:
		subprocess.Popen(command, shell=True)
	else:
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