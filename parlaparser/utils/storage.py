from parlaparser import settings
from parlaparser.utils.parladata_api import ParladataApi

from collections import defaultdict
from datetime import datetime

import logging
import editdistance


class NoneError(Exception):
    pass


class DataStorage(object):
    people = {}
    organizations = {}
    votes = {}
    motions = {}
    sessions = {}
    sessions_with_speeches = []
    sessions_speech_count = {}
    sessions_in_review = []
    questions = {}
    legislation = {}
    acts = {}
    agenda_items = {}
    memberships = defaultdict(lambda: defaultdict(list))

    legislation_classifications = {}
    procedures = {}
    procedure_phases = {}
    legislation_considerations = {}
    legislation_statuses = {}

    mandate_id = settings.MANDATE
    main_org_id = settings.MAIN_ORG_ID
    # old end

    def __init__(self):
        logging.warning(f'Start loading data')
        self.parladata_api = ParladataApi()
        for person in self.parladata_api.get_people():
            if not person['parser_names']:
                continue
            self.people[person['parser_names'].lower()] = person['id']
        logging.warning(f'loaded {len(self.people)} people')


        for org in self.parladata_api.get_organizations():
            if not org['parser_names']:
                continue
            self.organizations[org['parser_names'].lower()] = org['id']
            if org['classification'] == 'pg':
                pass
                # TODO od remove
                #self.klubovi[org['id']] = org['name']
        logging.warning(f'loaded {len(self.organizations)} organizations')
        for vote in self.parladata_api.get_votes():
            self.votes[self.get_vote_key(vote)] = vote['id']
        logging.warning(f'loaded {len(self.votes)} votes')

        for _session in self.parladata_api.get_sessions():
            self.sessions[self.get_session_key(_session)] = _session['id']
            if _session['in_review']:
                self.sessions_in_review.append(_session['id'])
        logging.warning(f'loaded {len(self.sessions)} sessions')

        # for session in self.sessions.values():
        #     speeche_count = self.parladata_api.get_session_speech_count(session_id=session)
        #     self.sessions_speech_count[session] = speeche_count
        #     if speeche_count > 0:
        #         self.sessions_with_speeches.append(speeche_count)

        for motion in self.parladata_api.get_motions():
            self.motions[self.get_motion_key(motion)] = motion['id'] # TODO check if is key good key
        logging.warning(f'loaded {len(self.motions)} motions')

        for item in self.parladata_api.get_agenda_items():
            self.agenda_items[self.get_agenda_key(item)] = item['id']
        logging.warning(f'loaded {len(self.agenda_items)} agenda_items')

        # for question in self.parladata_api.get_questions():
        #     self.questions[self.get_question_key(question)] = {'id': question['id'], 'answer': question['answer_timestamp']}
        # logging.warning(f'loaded {len(self.questions)} questions')

        for legislation in self.parladata_api.get_legislation():
            self.legislation[legislation['epa']] = legislation

        logging.debug(self.people.keys())
        api_memberships = self.parladata_api.get_memberships()
        for membership in api_memberships:
            self.memberships[membership['organization']][membership['member']].append(membership)
        logging.warning(f'loaded {len(api_memberships)} memberships')


        api_legislation_classifications = self.parladata_api.get_legislation_classifications()
        for legislation_classification in api_legislation_classifications:
            self.legislation_classifications[legislation_classification['name']] = legislation_classification['id']

        api_procedures = self.parladata_api.get_procedures()

        for procedure in api_procedures:
            self.procedures[procedure['type']] = procedure['id']

        api_procedure_phases = self.parladata_api.get_procedure_phases()
        for procedure_phase in api_procedure_phases:
            self.procedure_phases[procedure_phase['name']] = procedure_phase

        api_legislation_considerations = self.parladata_api.get_legislation_consideration()
        for legislation_consideration in api_legislation_considerations:
            self.legislation_considerations[self.get_legislation_consideration_key(legislation_consideration)] = legislation_consideration['id']

        api_legislation_statuses = self.parladata_api.get_legislation_statuses()
        for legislation_status in api_legislation_statuses:
            self.legislation_statuses[legislation_status['name']] = legislation_status['id']



    def get_vote_key(self, vote):
        if vote['name'] == None:
            raise NoneError
        return (vote['name']).strip().lower()

    def get_motion_key(self, motion):
        return (motion['gov_id'] if motion['gov_id'] else '').strip().lower()

    def get_session_key(self, session):
        return session['name'].strip().lower()

    def get_question_key(self, question):
        return (question['title'] + question['timestamp'] + question['recipient_text']).strip().lower()

    def get_agenda_key(self, agenda_item):
        return f'{agenda_item["session"]} {agenda_item["order"]}'

    def get_legislation_consideration_key(self, legislation_consideration):
        return f'{legislation_consideration["timestamp"]}_{legislation_consideration["legislation"]}_{legislation_consideration["procedure_phase"]}'

    def get_id_by_parsername(self, object_type, name):
        """
        """
        try:
            name = name.lower()
        except:
            return None
        for parser_names in getattr(self, object_type).keys():
            for parser_name in parser_names.split('|'):
                if editdistance.eval(name, parser_name.lower()) == 0:
                    return getattr(self, object_type)[parser_names]
        return None

    def get_id_by_parsername_compare_rodilnik(self, object_type, name):
        """
        """
        cutted_name = [word[:-2] for word in name.lower().split(' ')]
        for parser_names in getattr(self, object_type).keys():
            for parser_name in parser_names.split('|'):
                cutted_parser_name = [word[:-2] for word in parser_name.lower().split(' ')]
                if len(cutted_parser_name) != len(cutted_name):
                    continue
                result = []
                for i, parted_parser_name in enumerate(cutted_parser_name):
                    result.append( parted_parser_name in cutted_name[i] )
                if result and all(result):
                    return getattr(self, object_type)[parser_names]
        return None

    def get_or_add_object_by_parsername(self, object_type, name, data_object, create_if_not_exist=True, name_type='normal'):
        if name_type == 'genitive':
            object_id = self.get_id_by_parsername_compare_rodilnik(object_type, name)
        else:
            object_id = self.get_id_by_parsername(object_type, name)
        added = False
        if not object_id:
            if not create_if_not_exist:
                return None, False
            if object_type == 'people':
                response = self.parladata_api.set_person(data_object)
            else:
                response = self.parladata_api.set_object(object_type, data_object)
            try:
                response_data = response.json()
                object_id = response_data['id']
                getattr(self, object_type)[response_data['parser_names'].lower()] = object_id
                added = True
            except Exception as e:
                raise Exception(f'Cannot add {object_type} {name} {response.json()} {e}')
                return None, False
        return object_id, added

    def get_or_add_person(self, name, data_object=None, name_type='normal'):
        if not data_object:
            data_object = {
                'name': name.strip().title(),
                'parser_names': name.strip()
            }
        return self.get_or_add_object_by_parsername('people', name, data_object, True, name_type=name_type)

    def get_person(self, name):
        return self.get_or_add_object_by_parsername('people', name, {}, False, name_type='normal')

    def add_person_parser_name(self, person_id, parser_name):
        person = self.parladata_api.add_person_parser_name(person_id, parser_name)
        self.people[person['parser_names'].lower()] = person['id']
        return person

    def get_or_add_organization(self, name, data_object):
        return self.get_or_add_object_by_parsername('organizations', name, data_object, True)

    def get_documents(self, tag):
        return self.parladata_api.get_documents(tag=tag)

    def get_links(self, tag):
        return self.parladata_api.get_links(tag=tag)

    def add_membership(self, data):
        membership = self.parladata_api.set_membership(data)
        if data['role'] == 'voter':
            logging.warning(membership)
            self.memberships[membership['organization']][membership['member']].append(membership)
        return membership

    def add_org_membership(self, data):
        membership = self.parladata_api.set_org_membership(data)
        return membership

    def add_or_get_session(self, data):
        key = self.get_session_key(data)
        if key in self.sessions:
            return self.sessions[key], False
        else:
            data.update(mandate=self.mandate_id)
            session_data = self.parladata_api.set_session(data)
            self.sessions[key] = session_data['id']
            return session_data['id'], True

    def unvalidate_speeches(self, session_id):
        self.parladata_api.unvalidate_speeches(session_id)

    def add_speeches(self, data):
        self.parladata_api.set_speeches(data)

    def set_ballots(self, data):
        added_ballots = self.parladata_api.set_ballots(data)

    def set_motion(self, data):
        added_motion = self.parladata_api.set_motion(data)
        return added_motion

    def get_or_add_agenda_item(self, data):
        logging.warning(self.get_agenda_key(data))
        logging.warning(self.agenda_items.keys())
        if self.get_agenda_key(data) in self.agenda_items.keys():
            return self.agenda_items[self.get_agenda_key(data)]
        else:
            added_agenda_item = self.parladata_api.set_agenda_item(data)
            return added_agenda_item['id']

    def set_legislation_consideration(self, data):
        legislation_consideration = self.parladata_api.set_legislation_consideration(data).json()
        self.legislation_considerations[self.get_legislation_consideration_key(legislation_consideration)] = legislation_consideration
        return legislation_consideration

    def check_if_motion_is_parsed(self, motion):
        key = self.get_motion_key(motion)
        return key in self.motions.keys()

    def check_if_question_is_parsed(self, question):
        key = self.get_question_key(question)
        return key in self.questions.keys()

    def set_vote(self, data):
        added_vote = self.parladata_api.set_vote(data)
        return added_vote

    def set_area(self, data):
        added_area = self.parladata_api.set_area(data)
        return added_area.json()

    def set_question(self, data):
        added_question = self.parladata_api.set_question(data)
        return added_question

    def set_link(self, data):
        added_link = self.parladata_api.set_link(data)
        return added_link

    def patch_motion(self, id, data):
        self.parladata_api.patch_motion(id, data)

    def patch_session(self, id, data):
        self.parladata_api.patch_session(id, data)

        # remove session from sessions_in_review if setted to in_review=False
        if not data.get('in_review', True):
            self.sessions_in_review.remove(id)
        # add session to sessions_in_review if setted to in_review=True
        if data.get('in_review', False):
            self.sessions_in_review.append(id)

    def patch_vote(self, id, data):
        self.parladata_api.patch_vote(id, data)

    def patch_document(self, id, data):
        self.parladata_api.patch_document(id, data)

    def patch_link(self, id, data):
        self.parladata_api.patch_link(id, data)

    def patch_legislation(self, id, data):
        self.parladata_api.patch_legislation(id, data)

    def patch_memberships(self, id, data):
        self.parladata_api.patch_memberships(id, data)

    def set_legislation(self, data):
        added_legislation = self.parladata_api.set_legislation(data)
        self.legislation[added_legislation['epa']] = added_legislation
        return added_legislation

    def is_membership_parsed(self, person_id, org_id, role):
        if not org_id in self.memberships.keys():
            return False
        if not person_id in self.memberships[org_id].keys():
            return False
        for membership in self.memberships[org_id][person_id]:
            if membership['role'] == role:
                return True
        return False


    def get_membership_of_member_on_date(self, person_id, search_date, core_organization):
        memberships = self.memberships[core_organization]
        if person_id in memberships.keys():
            # person in member of parliamnet
            mems = memberships[person_id]
            for mem in mems:
                start_time = datetime.strptime(mem['start_time'], "%Y-%m-%dT%H:%M:%S")
                if start_time <= search_date:
                    if mem['end_time']:
                        end_time = datetime.strptime(mem['end_time'], "%Y-%m-%dT%H:%M:%S")
                        if end_time >= search_date:
                            return mem['on_behalf_of']
                    else:
                        return mem['on_behalf_of']
        return None
