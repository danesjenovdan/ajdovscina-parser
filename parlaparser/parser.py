from parlaparser.utils.storage import DataStorage

from datetime import datetime
from collections import defaultdict

import json
import xlrd
import requests

OPTION_MAP = {
    'Proti': 'against',
    'Se ni prijavil/a': 'absent',
    'Za': 'for',
    'Ni glasoval/a': 'abstain'
}

class Parser(object):
    def __init__(self):
        self.storage = DataStorage()
        self.parsable_documents = self.storage.get_documents(tag='parsable')

    def parse(self):
        for document in self.parsable_documents:
            # skip parsed files
            if 'parsed' in document['tags']:
                print('skup document')
                continue

            print('start parsing document')

            self.load_document(document['file'])
            parsed_data = self.parse_doc()
            session_id = None

            data = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))

            # prettify data structure
            for person in parsed_data:
                person_id, added_person = self.storage.get_or_add_person(
                    person['name']
                )
                for agenda_item in person['agenda_items']:
                    for vote in agenda_item['votes']:
                        vote_with_voter = vote
                        vote_with_voter.update(voter=person_id)
                        data[agenda_item['name']][vote["name"]]['ballots'].append(vote_with_voter)
                        if vote['maybe_datetime']:
                            data[agenda_item['name']][vote["name"]]['datetime'] = vote['maybe_datetime']
                            data[agenda_item['name']][vote["name"]]['session_name'] = vote['session_name']
                            data[agenda_item['name']][vote["name"]]['title'] = vote['name']

            # save data
            for agenda_order, (agenda_item, votes) in enumerate(data.items()):
                agenda_item_id = None
                legislation_id = None
                for vote_order, (vote, vote_object) in enumerate(votes.items()):
                    #print(vote_object)
                    vote_id = None
                    ballots_for_save = []
                    start_time = vote_object['datetime']
                    title = vote_object['title']
                    print('Adding agenda item', agenda_item, agenda_order)

                    if not session_id:
                        session_id, added = self.storage.add_or_get_session({
                            'name': vote_object['session_name'],
                            'organizations': [self.storage.main_org_id],
                            'start_time': start_time.isoformat()
                        })
                        print('Adding session', vote_object['session_name'])
                    if not agenda_item_id:
                        agenda_item_id = self.storage.get_or_add_agenda_item({
                            'name': agenda_item,
                            'datetime': start_time.isoformat(),
                            'session': session_id,
                            'order': agenda_order
                        })
                        if 'odlok' in agenda_item.lower():
                            legislation_obj = self.data_storage.set_legislation({
                                'text': agenda_item,
                                'session': session_id,
                                'timestamp': start_time.isoformat(),
                                'classification': self.storage.legislation_classification['decree'],
                            })
                            legislation_id = legislation_obj['id']

                    if not vote_id:
                        motion = {
                            'title': title,
                            'text': title,
                            'datetime': start_time.isoformat(),
                            'session': session_id,
                            'agenda_items': [agenda_item_id]
                        }
                        if legislation_id:
                            motion['law'] = legislation_id
                        motion_obj = self.storage.set_motion(motion)
                        new_vote = {
                            'name': title,
                            'timestamp': start_time.isoformat(),
                            'session': session_id,
                            'motion': motion_obj['id']
                        }
                        vote_obj = self.storage.set_vote(new_vote)
                        vote_id = vote_obj['id']

                    for ballot in vote_object['ballots']:
                        ballots_for_save.append(
                            {
                                'personvoter': ballot['voter'],
                                'option': self.get_ballot_option(ballot['ballot']),
                                'vote': vote_id
                            }
                        )

                    self.storage.set_ballots(ballots_for_save)

            self.storage.patch_document(document['id'], {
                'tags': ['parsable', 'parsed']
            })

    def get_ballot_option(self, option):
        try:
            out_option = OPTION_MAP[option]
        except:
            out_option = None
        return out_option


    def load_document(self, url):
        response = requests.get(url)
        with open(f'parlaparser/files/temp_file.xls', 'wb') as f:
            f.write(response.content)

        self.book = xlrd.open_workbook('parlaparser/files/temp_file.xls')

    def parse_doc(self):
        sheet = self.book.sheet_by_index(0)

        # iterate through all the rows in the sheet
        # and store cell values in memory as lists
        rows = []
        for row_i in range(sheet.nrows):
            row_values = []
            for cell in sheet.row(row_i):
                row_values.append(cell.value.strip())
            rows.append(row_values)

        # for row in rows:
        #     print(row)

        # get session name
        session_name = rows[0][-5]

        # get all rows where individual members'
        # votes begin (they contain members' names)
        row_indices_with_names = []
        for i, row in enumerate(rows):
            if 'Ime in priimek' in row:
                row_indices_with_names.append(i)

        # this is where we will store our member data
        members = []

        # we need to calculate how many rows each member has to process
        number_of_person_rows = row_indices_with_names[1] - row_indices_with_names[0]

        for i, person_index  in enumerate(row_indices_with_names):
            # append the member
            members.append({
                'person_index': person_index, # person_index for debugging purposes
                'name': rows[person_index][-10], # 10th column in the first row
                'party': rows[person_index + 1][-10], # 10th column in the second row
                'agenda_items': [], # create a list for members' legislation
            })
            # person_index + 5 contains headings for the voting results
            # column indexes follow:
            # Zap. št. => 1
            # Sklep => 4
            # Odziv => 8
            # Datum in čas oddaje odziva => 12
            # Čas oddaje odziva => 14

            # we now need to iterate through all the rows until we reach
            # the next person. that's why we calculated number_of_person_rows

            # we need to track legislation indexes, starting with -1
            # so we can +1 every iteration
            agena_item_index = -1
            for voting_row_index in range(person_index + 6, person_index + number_of_person_rows):
                # if only the second cell is full, this is a title and we save
                # it as the legislation name
                if len([cell for cell in rows[voting_row_index] if cell == '']) == 14 and rows[voting_row_index][1] != '':
                    members[i]['agenda_items'].append({
                        'name': rows[voting_row_index][1],
                        'votes': []
                    })
                    agena_item_index += 1
                else:
                    #there is no vote datetime if the person did not vote
                    if rows[voting_row_index][8] in ['Ni glasoval/a', 'Se ni prijavil/a']:
                        maybe_vote_datetime = None
                    else:
                        try:
                            maybe_vote_datetime = datetime.strptime(rows[voting_row_index][12], '%d.%m.%Y %H:%M:%S')
                        except:
                            print(rows[voting_row_index])

                    members[i]['agenda_items'][agena_item_index]['votes'].append({
                        'order': rows[voting_row_index][1],
                        'name': rows[voting_row_index][4],
                        'ballot': rows[voting_row_index][8],
                        'maybe_datetime': maybe_vote_datetime,
                        'datetime_format': '%d.%m.%Y %H:%M:%S',
                        'session_name': session_name
                    })

        return members

