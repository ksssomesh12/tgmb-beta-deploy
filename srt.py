import re

if __name__ == '__main__':
    fPipfile = '../Pipfile'
    fRequirements = 'requirements.txt'
    with open(fPipfile, 'rt') as fP:
        pipfileContents = fP.read()
    requiredPackages: list[str] = [
        "google-api-python-client",
        "google-auth-httplib2",
        "google-auth-oauthlib",
        "python-magic"
    ]
    requirementsContents = ""
    for requiredPackage in requiredPackages:
        rSearch = requiredPackage + r" = \"==([0-9.]+)\""
        sSearch: list[str] = re.findall(rSearch, pipfileContents)
        requirementsContents += requiredPackage + "==" + sSearch[0] + "\n"
    with open(fRequirements, 'wt') as fR:
        fR.write(requirementsContents)
