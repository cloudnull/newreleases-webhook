import json
import os
import threading
import queue
import uuid

from flask import Flask
from flask import request
from flask import Response

from jira import JIRA


APP = Flask(__name__)
EVENT = threading.Event()
JIRA_API_TOKEN = os.environ.get("JIRA_API_TOKEN")
JIRA_USER_EMAIL = os.environ.get("JIRA_USER_EMAIL")
JIRA_PROJECT = os.environ.get("JIRA_PROJECT")
QUEUE = queue.Queue()
WEBHOOK_TOKEN = os.environ.get("WEBHOOK_TOKEN", str(uuid.uuid4()))


def _jira_auth():
    """Return a jira authentication object.

    If no authentication can be reached None is returned.
    """
    try:
        return JIRA(
            basic_auth=(JIRA_USER_EMAIL, JIRA_API_TOKEN),
        )
    except Exception as e:
        APP.logger.error("Jira authentication failed: {}".format(str(e)))


def _create_jira():
    """Create jira tickets from received webhooks."""

    while not EVENT.is_set():
        data = json.loads(QUEUE.get())
        if JIRA_USER_EMAIL and JIRA_API_TOKEN:
            jira = _jira_auth()
        else:
            jira = None

        with open('/opt/app/template') as f:
            item = dict(
                project=JIRA_PROJECT,
                summary=f'Project {data["project"]} has released {data["version"]},'
                        ' which may require an upgrade',
                description=f.read().format(**data['fields']),
                issuetype={"name": "Upgrade"},
            )

        if jira:
            try:
                jira.create_issue(**item)
            except Exception as e:
                APP.logger.error("Failed to create Jira issue: {}".format(str(e)))
                APP.logger.warning("re-authenticating")
                jira = _jira_auth()
                if jira:
                    APP.logger.warning("re-queuing")
                    QUEUE.put(json.dumps(data))
        else:
            # When there's no jira auth we echo the expected response
            APP.logger.info(item)


# NOTE(cloudnull): So that we're never blocked on jira creations the creation
#                  process is in a thread.
THREAD = threading.Thread(group=None, target=_create_jira, daemon=True)
THREAD.start()


@APP.route(f"/newreleases_webhook", methods=["POST"])
def newrelease():
    """Receive webooks.

    :returns: String
    """
    if request.headers.get("Token") != WEBHOOK_TOKEN:
        return Response("Missing Token", status=400)

    data = request.json
    if data:
        try:
            QUEUE.put(json.dumps(data))
        except Exception:
            return Response("Bad Data", status=400)

    return Response("OK", status=200)


if __name__ == "__main__":
    print(f"Token for this webhook {WEBHOOK_TOKEN}")
    APP.run(host="0.0.0.0", port=5000)
    EVENT.set()
