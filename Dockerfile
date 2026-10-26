ARG IRIS_IMAGE=proof-before-pay/iris-eap:2026.3.0AI.154.0
FROM ${IRIS_IMAGE}
WORKDIR /home/irisowner
COPY --chown=51773:51773 requirements.lock /opt/pbp/requirements.lock
RUN python3 -m pip install --no-cache-dir --no-deps --require-hashes \
    --target /home/irisowner/pbp-deps -r /opt/pbp/requirements.lock
COPY --chown=51773:51773 python /opt/pbp/python
COPY --chown=51773:51773 cls /opt/pbp/cls
COPY --chown=51773:51773 tests /opt/pbp/tests
COPY --chown=51773:51773 fixtures /opt/pbp/fixtures
COPY --chown=51773:51773 scripts /opt/pbp/scripts
COPY --chown=51773:51773 merge.cpf /opt/pbp/merge.cpf
ENV PYTHONPATH="/home/irisowner/pbp-deps:/opt/pbp/python"
ENV ISC_CPF_MERGE_FILE=/opt/pbp/merge.cpf
CMD ["--ISCAgent", "false", "--after", "sh /opt/pbp/scripts/initialize.sh"]
