"""Release receipts bind approval to exact content; reviews cannot be invented."""

from copy import deepcopy

import pytest

from heart.locales import RESOURCE_VERSION
from heart.localization.batch import digest
from heart.localization.release import validate_release


def package():
    records = [dict(locale='en', draft={'cover_url':'/api/profile/cover-file/example.webp'},
        human_reviewed=False, published=True, review_status='owner_authorized_release')]
    receipt = dict(schema_version=1, release_id='test', batch_id='test',
        authorization=dict(by='project_owner', request='SYNTHETIC TEST', date='2026-10-13', scope='test'),
        resource_version=RESOURCE_VERSION, package_sha256=digest(records),
        edition_counts={'en':1}, review_evidence={'human_reviewed':False})
    return records, receipt


def test_exact_content_and_authorization_are_required():
    records, receipt = package()
    validate_release(records, receipt)
    with pytest.raises(ValueError, match='authorized digest'):
        validate_release([*records, *records], receipt)
    with pytest.raises(ValueError, match='authorization'):
        validate_release(records, {**receipt, 'authorization':{}})
    with pytest.raises(ValueError, match='Stale'):
        validate_release(records, {**receipt, 'resource_version':'old'})
    with pytest.raises(ValueError, match='counts'):
        validate_release(records, {**receipt, 'edition_counts':{'en':2}})


@pytest.mark.parametrize('cover', ['http://localhost:9000/cover','https://external.example/cover','//localhost/cover'])
def test_local_and_external_media_are_rejected(cover):
    records, receipt = package()
    changed = deepcopy(records)
    changed[0]['draft']['cover_url'] = cover
    with pytest.raises(ValueError, match='production origin'):
        validate_release(changed, {**receipt, 'package_sha256':digest(changed)})


def test_owner_approval_does_not_claim_specialist_review():
    records, receipt = package()
    records[0]['human_reviewed'] = True
    with pytest.raises(ValueError, match='specialist review'):
        validate_release(records, {**receipt, 'package_sha256':digest(records)})
