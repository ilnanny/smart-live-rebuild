#	vim:fileencoding=utf-8
# (c) 2011 Michał Górny <mgorny@gentoo.org>
# Released under the terms of the 2-clause BSD license.

import errno, fcntl, os, select, shutil, subprocess, tempfile

class BashParser(object):
	def __init__(self):
		self._tmpf = tempfile.NamedTemporaryFile('w+b')
		self._bashproc = subprocess.Popen(['bash', '-c',
				'while read -r SLR_VARS; do ( source %s; eval set -- ${SLR_VARS}; printf "%%s\\0" "${@}" ); done' % self._tmpf.name],
			stdin = subprocess.PIPE, stdout = subprocess.PIPE)

		fd = self._bashproc.stdout
		fcntl.fcntl(fd, fcntl.F_SETFL, os.O_NONBLOCK | fcntl.fcntl(fd, fcntl.F_GETFL))

	def grabenv(self, envf):
		f = self._tmpf
		f.seek(0, 0)
		f.truncate(0)
		shutil.copyfileobj(envf, f)
		f.flush()

	def __call__(self, vars):
		# File ready, now ping the server...
		self._bashproc.stdin.write(('%s\n' % ' '.join(['"${%s}"' % x for x in vars])).encode('ASCII'))
		self._bashproc.stdin.flush()

		# ...and grab the output (hopefully, we're in non-blocking mode).
		l = bytes()
		spl = []
		while len(spl) <= len(vars):
			select.select((self._bashproc.stdout,), (), (), 5)
			try:
				ret = self._bashproc.stdout.read()
				if ret is None:
					continue
				l += ret
			except IOError as e:
				if e.errno not in (errno.EAGAIN, errno.EWOULDBLOCK):
					raise
			else:
				try:
					# the environment file should be utf8-encoded
					spl = l.decode('utf8').split('\0')
				except UnicodeError:
					# got stuck in the middle of a character?
					spl = []

		return dict(zip(vars, spl))

	def terminate(self):
		self._bashproc.terminate()
		self._bashproc.communicate()
		self._tmpf.close()