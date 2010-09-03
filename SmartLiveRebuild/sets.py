#	vim:fileencoding=utf-8
# (c) 2010 Michał Górny <gentoo@mgorny.alt.pl>
# Released under the terms of the 3-clause BSD license or the GPL-2 license.

try:
	from portage.sets.base import PackageSet
	from portage.sets import SetConfigError
except ImportError:
	from portage._sets.base import PackageSet
	from portage._sets import SetConfigError

from SmartLiveRebuild.core import Config, SmartLiveRebuild, SLRFailure

class SmartLiveRebuildSet(PackageSet):
	_operations = ["merge"]
	description = "Package set containing live packages awaiting update"

	def __init__(self, opts, dbapi, settings):
		self._options = opts
		self._dbapi = dbapi
		self._settings = settings
		PackageSet.__init__(self)

	def load(self):
		try:
			packages = SmartLiveRebuild(self._options,
					db = self._dbapi, saveuid = True)
		except SLRFailure:
			pass
		else:
			self._setAtoms('>=%s' % p for p in packages)

			if self._options.offline:
				s = self._settings
				s.unlock()
				s['ESCM_OFFLINE'] = 'true'
				s.backup_changes('ESCM_OFFLINE')
				s.lock()

	@classmethod
	def singleBuilder(cls, options, settings, trees):
		# Clasically, apply twice. First time to get configfile path
		# and profile; second time to override them.
		c = Config(settings)
		c.apply_dict(options)
		c.parse_configfiles()
		c.apply_dict(options)

		db = trees['vartree'].dbapi

		return cls(c.get_options(), db, settings)
