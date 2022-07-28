ARG VERSION=0.0.1

FROM alpine:latest as BUILD
RUN apk add python3-dev build-base linux-headers pcre-dev py3-pip
RUN python3 -m venv /opt/jira-webhook
RUN /opt/jira-webhook/bin/python3 -m pip install --upgrade pip; /opt/jira-webhook/bin/python3 -m pip install uwsgi flask jira

FROM alpine:latest
RUN apk add python3 pcre
COPY --from=BUILD /opt/jira-webhook /opt/jira-webhook
WORKDIR /opt/app
ADD app.py /opt/app/app.py
ADD template /opt/app/template
ADD entrypoint /entrypoint
EXPOSE 5000
USER 1000
ENTRYPOINT ["/entrypoint"]
