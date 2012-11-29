import re

from helper import url_fetch, get_session_key

"""Facilitates getting information about FIRST teams"""

TPID_URL = "https://my.usfirst.org/myarea/index.lasso?page=searchresults&programs=FRC&reports=teams&sort_teams=number&results_size=250&omit_searchform=1&season_FRC=%s&skip_teams=%s"
TEAMLIST_URL = "https://my.usfirst.org/frc/scoring/index.lasso?page=teamlist"
TEAM_DETAILS_URL = "https://my.usfirst.org/myarea/index.lasso?page=team_details&tpid=%s&-session=myarea:%s"


def get_basic_team_info():
	"""
	Facilitates getting information about Teams from FIRST. Reads from FMS
	data pages, which are mostly tab delimited files wrapped in some HTML.
	Note, this can only get info on teams in current season
	"""
	return _parse_basic_team_info(url_fetch(TEAMLIST_URL))


def _parse_basic_team_info(soup):
	"""
	Parse the information table on USFIRSTs site to extract team information.
	Return a list of dictionaries of team data.
	"""
	teams = []

	# for title in soup.findAll('title'):
	# 	if title.string != '2012 FRC Team/Event List':
	# 		return None

	# first is blank, second is headers.
	team_rows = soup.findAll('pre')[0].string.split('\n')[2:]

	for line in team_rows:
		data = line.split('\t')
		if len(data) > 1:
			try:
				teams.append({
					'team_number': int(data[1]),
					'name': data[2],
					'short_name': data[3],
					'address': '%s, %s, %s' % (data[4], data[5], data[6]),
					'nickname': data[7],
				})
			except:
				raise Exception('Failed to parse team row: %s' % data)

	return teams


def get_team_details(tpid, year):
	"""Return a Team object for the requested team_number"""

	session_key = get_session_key(year)
	url = TEAM_DETAILS_URL % (tpid, session_key)

	return parse_team_details(url_fetch(url))


def parse_team_details(soup):
	"""Parse the information table on USFIRSTs site to extract relevant team
	information. Return a Team object"""
	team = {}

	if soup.find(text='No team found.') is not None:
		raise Exception('team not found')

	for tr in soup.findAll('tr')[3:]:  # first 4 are garbage
		tds = tr.findAll('td')
		if len(tds) > 1:
			field = tds[0].string
			if field == 'Team Number':
				team['team'] = int(tds[1].b.string)
			elif field == 'Team Name':
				team['name'] = tds[1].string
			elif field == 'Team Location':
				#TODO: Filter out &nbsp;'s & stuff
				team['location'] = unicode(tds[1].string)
			elif field == 'Rookie Season':
				team['rookie_year'] = int(tds[1].string)
			elif field == 'Team Nickname':
				team['nickname'] = unicode(tds[1].string)
			elif field == 'Team Website':
				#try:
				team['website'] = tds[1].a['href']
				#except Exception:
				#	raise Exception('Team website is invalid for team %s.' % team['number'])
			elif field == 'Team History':

				team['events'] = []
				for row in tds[1].findAll('tr')[1:]:
					event = row.findAll('td')

					awards = []
					unfiltered_awards = event[2].contents
					for award in unfiltered_awards:
						# filter out all the tags n' whitespace n' shit
						if award.__class__.__name__ == 'NavigableString' and award.strip() != '':
							awards.append(award.strip())  # it is really an award, add to the list

					team['events'].append({
						'year': int(event[0].string),
						'event': event[1].string[5:],
						'awards': awards
					})

				# team history is the last part of the page return here to
				# avoid looping through other stuff
				return team


# Separates tpids on the FIRST list of all teams.
teamRe = re.compile(r'tpid=[A-Za-z0-9=&;\-:]*?"><b>\d+')
# Extracts the team number from the team result.
teamNumberRe = re.compile(r'\d+$')
# Extracts the tpid from the team result.
tpidRe = re.compile(r'\d+')
# Extracts the link to the next page of results on the FIRST list of all teams.
lastPageRe = re.compile(r'Next ->')


def get_tpids(year):
	tpid_list = []
	skip = 0
	TPID_RE = re.compile(r'tpid=([0-9]*)')

	while True:
		url = TPID_URL % (year, skip)

		soup = url_fetch(url)

		try:
			content = soup.p.td.table.findAll('tr')  # sort through badly written html
		except:
			raise Exception('invalid data returned for %s FRC season' % year)

		try:
			content[3]  # check if there is anything... tells if we got to end of list
		except IndexError:
			return tpid_list  # end of list, return now

		for team_row in content[3:]:  # first 3 are garbage
			tpid_list.append({
				'team': int(team_row.b.contents[0]),
				'tpid': int(TPID_RE.search(team_row.a['href']).group(1))
			})

		skip += 250  # increase skip and loop to get another page
