import io,json,zipfile

def package_artifacts(artifacts:dict[str,bytes],manifest:dict)->bytes:
    out=io.BytesIO()
    with zipfile.ZipFile(out,"w",zipfile.ZIP_DEFLATED) as z:
        for name,data in artifacts.items(): z.writestr(name,data)
        z.writestr("manifest.json",json.dumps(manifest,indent=2,default=str))
    return out.getvalue()
