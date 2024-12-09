


---

🚨⚠️ PLEASE NOTE ⚠️🚨

After merging changes into the main branch the utils repository, the base image will automatically be rebuilt, but then every other application image will also need to be rebuilt across environments on top of that.
This is to identify any issues that may crop up across consumer applications from making changes to utils (e.g., bumping package versions) early on.
If this is not done, it can obfuscate the origin of an issue were it to show up later.
