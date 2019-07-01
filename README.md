**NOTE**: _a rather comfortable library seems to exist with [hapy](https://github.com/WilliamMayor/hapy)!_

---

python-heritrix
---------------

A simple wrapper around the Heritrix 3.x API:

  https://webarchive.jira.com/wiki/display/Heritrix/Heritrix+3.x+API+Guide
  
or newer (old is redirect):

  https://heritrix.readthedocs.io/en/latest/api.html

Developed in April 2012 against Heritrix 3.1.0 at GWU Libraries in
Washington, DC, USA.


known issues
------------

Ubuntu versions later than 10.04 LTS ship with an openssl version that
leads to the SSL error noted in the API guide (link above).  This does
not occur with 10.04 LTS.

Disable `InsecureRequestWarning` warnings for un-verified https requests:

```python
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
```

todo
----

Add some more scripts to API?:

  https://github.com/internetarchive/heritrix3/wiki/Heritrix3%20Useful%20Scripts#Heritrix3UsefulScripts-dumpsurts
