import logging
import os

import requests
from lxml import etree
from requests.auth import HTTPDigestAuth

requests_log = logging.getLogger("requests")
requests_log.setLevel(logging.WARNING)

# ---------------------------------------------------------------------------


class HeritrixAPIError(Exception):
    def __init__(self, message):
        self.message = message
        super(HeritrixAPIError, self).__init__(message)

    def __str__(self):
        return "HeritrixAPIError: {}".format(self.message)


class HeritrixAPI(object):
    def __init__(
        self,
        host="https://localhost:8443/engine",
        user="admin",
        passwd="",
        verbose=False,
        verify=False,
        headers=None,
    ):
        self.host = host
        self.user = user
        self.passwd = passwd
        self.verbose = verbose
        self.verify = verify

        # strip trailing slashes
        if self.host:
            self.host = self.host.rstrip("/")

        self.headers = {"Accept": "application/xml"}
        if isinstance(headers, dict):
            self.headers.update(headers)

    def _post(self, url=None, data=None, headers=None):
        if not url:
            url = self.host

        headers_copy = dict(self.headers)
        if headers is not None:
            headers_copy.update(headers)

        if data is None:
            data = dict()

        resp = requests.post(
            url,
            auth=HTTPDigestAuth(self.user, self.passwd),
            data=data,
            headers=headers_copy,
            verify=self.verify,
        )
        return resp

    def _get(self, url=None, headers=None, api_headers=True):
        if not url:
            url = self.host

        headers_copy = dict()
        if api_headers:
            headers_copy.update(self.headers)
        if headers is not None:
            headers_copy.update(headers)

        resp = requests.get(
            url,
            auth=HTTPDigestAuth(self.user, self.passwd),
            headers=headers_copy,
            verify=self.verify,
        )
        return resp

    def _post_action(self, action, url=None, data=None, headers=None):
        if action is None or action == "":
            raise HeritrixAPIError("Missing action.")

        if data is None:
            data = dict()

        data["action"] = action

        return self._post(url=url, data=data, headers=headers)

    def _job_action(self, action, job_name, data=None):
        if job_name is None or job_name == "":
            raise HeritrixAPIError("Missing job name.")

        url = "{host}/job/{job}".format(host=self.host, job=job_name)

        return self._post_action(action, url, data=data)

    # --------------------------------

    def create(self, job_name):
        if job_name is None or job_name == "":
            raise HeritrixAPIError("Missing job name.")

        return self._post_action("create", data={"createpath": job_name})

    def add(self, job_dir):
        if job_dir is None or job_dir == "":
            raise HeritrixAPIError("Missing job directory.")
        # TODO: check that a cxml file is in the directory?

        return self._post_action("add", data={"addpath": job_dir})

    # --------------------------------

    def build(self, job_name):
        return self._job_action("build", job_name)

    def launch(self, job_name, checkpoint=None):
        data = None
        if checkpoint is not None:
            data = {"checkpoint": checkpoint}

        return self._job_action("build", job_name, data=data)

    def pause(self, job_name):
        return self._job_action("build", job_name)

    def unpause(self, job_name):
        return self._job_action("unpause", job_name)

    def terminate(self, job_name):
        return self._job_action("terminate", job_name)

    def teardown(self, job_name):
        return self._job_action("teardown", job_name)

    def checkpoint(self, job_name):
        return self._job_action("checkpoint", job_name)

    # --------------------------------

    def rescan(self):
        return self._post_action("rescan")

    def copy(self, job_name, new_job_name, as_profile=False):
        if new_job_name is None or new_job_name == "":
            raise HeritrixAPIError("new_job_name must not be empty!")

        data = dict()
        data["copyTo"] = new_job_name
        if as_profile:
            data["as_profile"] = "on"

        return self._job_action("copy", job_name, data=data)

    # --------------------------------

    def execute_script(self, job_name, script, engine="beanshell"):
        if job_name is None or job_name == "":
            raise HeritrixAPIError("Missing job name.")
        if script is None or script == "":
            raise HeritrixAPIError("Missing script?")
        if engine not in ("beanshell", "js", "groovy", "AppleScriptEngine"):
            raise HeritrixAPIError("Invalid script engine param: {}".format(engine))

        data = dict()
        data["engine"] = "js"
        data["script"] = script

        url = "{host}/job/{job}/script".format(host=self.host, job=job_name)

        return self._post(url=url, data=data)

    # --------------------------------

    def send_config(self, job_name, cxml_filepath):
        if job_name is None or job_name == "":
            raise HeritrixAPIError("Missing job name.")
        if cxml_filepath is None or cxml_filepath == "":
            raise HeritrixAPIError("Missing cxml filepath name.")
        if not os.path.exists(cxml_filepath) or not os.path.isfile(cxml_filepath):
            raise HeritrixAPIError(
                "CXML file does not exist!, {}".format(cxml_filepath)
            )

        url = "{host}/job/{job}/jobdir/crawler-beans.cxml".format(
            host=self.host, job=job_name
        )

        with open(cxml_filepath, "rb") as fdat:
            resp = requests.put(
                url,
                auth=HTTPDigestAuth(self.user, self.passwd),
                data=fdat,
                headers=self.headers,
                verify=self.verify,
            )
        return resp.ok

    # --------------------------------

    def list_jobs(self, status=None, unbuilt=False):
        resp = self._get()
        xml_doc = etree.fromstring(resp.text)

        if unbuilt:
            # if unbuilt, then search for those only
            jobs = xml_doc.xpath("//jobs/value[./statusDescription = 'Unbuilt']")
        elif status is not None:
            # then search for crawlControllerState
            jobs = xml_doc.xpath(
                "//jobs/value[./crawlControllerState = '{}']".format(status)
            )
        else:
            # else all
            jobs = xml_doc.xpath("//jobs/value")

        job_names = [job.find("shortName").text for job in jobs]
        return job_names

    def get_launchid(self, job_name):
        script = "rawOut.println( appCtx.getCurrentLaunchId() );"
        resp = self.execute_script(job_name, script=script, engine="beanshell")
        if not resp.ok:
            if resp.status_code == 500:
                # most probably not application context / unbuilt job
                return None

            raise HeritrixAPIError(
                "No launchid found: {} - {}".format(resp.status_code, resp.reason)
            )

        tree = etree.fromstring(resp.text)
        return tree.find("rawOutput").text.strip()

    def crawl_report(self, job_name, launch_id=None):
        if launch_id is None:
            try:
                # if no launchid - try to get with "latest"
                url = "{host}/job/{job}/jobdir/latest/reports/crawl-report.txt".format(
                    host=self.host, job=job_name
                )

                resp = self._get(url=url, api_headers=False)
                return resp.text
            except Exception as ex:
                # if that fails, try to query the launch_id and try again
                launch_id = self.get_launchid(job_name)

                if launch_id is None:
                    # unbuilt job?
                    # either it got anything with latest or there simply was not yet a crawl
                    raise HeritrixAPIError(
                        "Unbuilt Job %s, check if has ever crawled?", job_name
                    ) from ex

                return self.crawl_report(job_name, launch_id=launch_id)

        # ----------------------------

        url = "{host}/job/{job}/jobdir/{id}/reports/crawl-report.txt".format(
            host=self.host, job=job_name, id=launch_id
        )

        resp = self._get(url=url, api_headers=False)
        return resp.text

    # ---------------------------------------------------------------------------
    # old

    def status(self, job_name):
        url = "{host}/job/{job}".format(host=self.host, job=job_name)
        xml = etree.fromstring(self._post(url).text)
        status = xml.find("crawlControllerState")
        if status is None:
            return ""
        else:
            return status.text

    def seeds(self, job_name):
        url = "{host}/job/{job}/jobdir/latest/seeds.txt".format(
            host=self.host, job=job_name
        )
        resp = self._get(url, api_headers=False)
        seeds = resp.text.split("\n")
        seeds = [seed.strip() for seed in seeds]  # hm?
        seeds = [seed for seed in seeds if seed]  # filter empty lines
        for i, seed in enumerate(seeds):
            if seed.startswith("#"):
                # stop at first comment?
                return seeds[0:i]
        return seeds

    def empty_frontier(self, job_name):
        script = (
            'count = job.crawlController.frontier.deleteURIs( ".*", "^.*" )'
            "\nrawOut.println count"
        )
        xml = self.execute_script(job_name, script, engine="groovy")
        tree = etree.fromstring(xml.content)
        return tree.find("rawOutput").text.strip()
