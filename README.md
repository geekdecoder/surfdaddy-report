# Surf Daddy's Market Surf Report

Daily public edition of Surf Daddy's Market Surf Report, the pre-market show from the cabana in Port Aransas, Texas.

`public/` holds the latest show and is replaced every weekday morning:

- `report.json`: the written report, market tape and captions
- `report.mp3`: the audio (Surf Daddy and Gus)

surfdaddy.surf/report pulls these files each morning. Information only, not investment advice.

`tools/build_audio.py` records each show (Surf Daddy's voice, Gus's bark, and the snack moment). The daily scheduled tasks download it from here, so changes to it apply to the next show automatically.
