#!/bin/bash
echo "parse sessions & votes"
python parser.py
cd /app
echo "start setting votes results"
python manage.py set_votes_result --majority relative_normal
# echo "start setting legislation results"
# python manage.py set_legislation_results
# echo "start setting motion tags"
# python manage.py set_motion_tags
# echo "start pairing votes with speeches"
# python manage.py pair_votes_and_speeches
# echo "lematize speeches"
# python manage.py lemmatize_speeches
# echo "set tfidf"
# python manage.py set_tfidf_for_sessions
echo "run analysis for today"
python manage.py daily_update
#echo "update legislation to solr"
#python manage.py upload_legislation_to_solr
# echo "update speeches to solr"
# python manage.py upload_speeches_to_solr
echo "update votes to solr"
python manage.py upload_votes_to_solr
# echo "send notifications"
# python manage.py send_daily_notifications
