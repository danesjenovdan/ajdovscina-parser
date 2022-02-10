import requests
import logging

from requests.auth import HTTPBasicAuth
from parlaparser import settings

logger = logging.getLogger('logger')


class ParladataApi(object):
    def __init__(self):
        self.auth = HTTPBasicAuth(settings.API_AUTH[0], settings.API_AUTH[1])
        self.base_url = settings.API_URL

    def _get_data_from_pager_api_gen(self, url, limit=300):
        end = False
        page = 1
        if '?' in url:
            url = url + f'&limit={limit}'
        else:
            url = url + f'?limit={limit}'
        logger.debug(url)
        while url:
            response = requests.get(url, auth=self.auth)
            if response.status_code != 200:
                logger.warning(response.content)
            data = response.json()
            yield data['results']
            url = data['next']

    def _get_objects(self, endpoint, limit=300, *args, **kwargs):
        url = f'{self.base_url}/{endpoint}'
        return [
            obj
            for page in self._get_data_from_pager_api_gen(url, limit)
            for obj in page]

    def _set_object(self, endpoint, data):
        response = requests.post(
                f'{self.base_url}/{endpoint}/',
                json=data,
                auth=self.auth
            )
        if response.status_code > 299:
            logger.warning(response.content)
        return response

    def _patch_object(self, endpoint, data):
        response = requests.patch(
                f'{self.base_url}/{endpoint}/',
                json=data,
                auth=self.auth
            )
        if response.status_code > 299:
            logger.warning(response.content)
        return response

    def set_object(self, endpoint, data):
        return self._set_object(endpoint, data)

    def get_people(self):
        return self._get_objects('people')

    def get_organizations(self):
        return self._get_objects('organizations')

    def get_votes(self):
        return self._get_objects('votes')

    def get_sessions(self):
        return self._get_objects('sessions')

    def get_motions(self):
        return self._get_objects('motions')

    def get_agenda_items(self):
        return self._get_objects('agenda-items')

    def get_questions(self):
        return self._get_objects('questions')

    def get_legislation(self):
        return self._get_objects('legislation')

    def get_legislation_classifications(self):
        return self._get_objects('legislation-classifications')

    def get_procedures(self):
        return self._get_objects('procedures')

    def get_procedure_phases(self):
        return self._get_objects('procedure-phases')

    def get_legislation_consideration(self):
        return self._get_objects('legislation-consideration')

    def set_legislation_consideration(self, data):
        return self._set_object('legislation-consideration', data)

    def get_legislation_statuses(self):
        return self._get_objects('legislation-status')

    def get_documents(self, tag):
        return self._get_objects(f'documents?tags__name={tag}')

    def get_links(self, tag):
        return self._get_objects(f'links?tags__name={tag}')

    def get_memberships(self, role=None):
        if role:
            role = f'?role=role'
        else:
            role = ''
        return self._get_objects(f'person-memberships/{role}')

    def patch_memberships(self, id, data):
        return self._patch_object(f'person-memberships/{id}', data).json()

    def get_speeches(self, id='', session=None):
        query = []
        if session:
            query.append(f'session={session}')
        if query:
            query = '?' + ('&'.join(query))
        return self._get_data_from_pager_api_gen(f'speeches/{id}{query}', limit=1)

    def get_session_speech_count(self, session_id):
        url = f'{self.base_url}/speeches/?session={session_id}'
        response = requests.get(url, auth=self.auth)
        return response.json()['count']

    def set_person(self, data):
        name = data.get('name', '')
        name, prefix = self.parse_name_prefix(name)
        if prefix:
            parser_names = data.pop('parser_names', '')
            parser_names += f'|{name}'
            data.update({
                'honorific_prefix': prefix,
                'parser_names': parser_names,
                'name': name,
            })
        logger.warning(data)
        return self._set_object('people', data)

    def add_person_parser_name(self, person_id, parser_name):
        return self._set_object(
            f'people/{person_id}/add_parser_name', {
            'parser_name': parser_name
        })

    def unvalidate_speeches(self, session_id):
        return self._set_object(
            f'sessions/{session_id}/unvalidate_speeches', {})

    def set_organization(self, data):
        return self._set_object('organizations', data)

    def set_area(self, data):
        return self._set_object('areas', data)

    def set_membership(self, data):
        return self._set_object('person-memberships', data).json()

    def set_org_membership(self, data):
        return self._set_object('organization-memberships', data).json()

    def set_session(self, data):
        return self._set_object('sessions', data).json()

    def set_speeches(self, data):
        return self._set_object('speeches', data).json()

    def set_ballots(self, data):
        return self._set_object('ballots', data).json()

    def set_motion(self, data):
        return self._set_object('motions', data).json()

    def patch_motion(self, id, data):
        return self._patch_object(f'motions/{id}', data).json()

    def patch_session(self, id, data):
        return self._patch_object(f'sessions/{id}', data).json()

    def patch_document(self, id, data):
        return self._patch_object(f'documents/{id}', data)

    def patch_link(self, id, data):
        return self._patch_object(f'links/{id}', data)

    def set_question(self, data):
        return self._set_object('questions', data).json()

    def set_link(self, data):
        return self._set_object('links', data).json()

    def set_vote(self, data):
        return self._set_object('votes', data).json()

    def patch_vote(self, id, data):
        return self._patch_object(f'votes/{id}', data).json()

    def set_legislation(self, data):
        return self._set_object('legislation', data).json()

    def patch_legislation(self, id, data):
        return self._patch_object(f'legislation/{id}', data).json()


    def set_agenda_item(self, data):
        return self._set_object('agenda-items', data).json()

    def upload_image(self, endpoint, url):
        file_name = f'parlaparser/files/{endpoint}.jpg'
        response = requests.get(url)
        with open(file_name, 'wb') as f:
            f.write(response.content)
        files = {'image': open(file_name, 'rb')}
        response = requests.patch(
                f'{self.base_url}/{endpoint}/',
                files=files,
                auth=self.auth
            )
        if response.status_code > 299:
            logger.warning(response.content)
        return response

    def parse_name_prefix(self, name):
        prefixes = [
            'dr',
            'mag',
            'prof'
        ]

        tokenized_name = name.split(' ')
        first_word = tokenized_name[0].replace('.', '').lower()

        prefix = None
        if first_word in prefixes:
            name = ' '.join(tokenized_name[1:])
            prefix = first_word

        return name, prefix
