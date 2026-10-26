from pathlib import Path
from urllib.request import urlopen


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "desktop" / "assets" / "stickers"
OUTPUT.mkdir(parents=True, exist_ok=True)
STICKERS = {
    "续火花": "https://p26-sign.douyinpic.com/obj/im-resource/1687263281313-ts-e7bbade781abe88ab12e706e67?lk3s=91c5b7cb&x-expires=1824552000&x-signature=L7lCSVPlVkGAeMxjMcMxgvM%2BPLM%3D&from=2445653963&s=im_111&se=false&sc=image&biz_tag=aweme_im&l=20261026204156D986D598F2E909EF52D2",
    "晚上好": "https://p26-sign.douyinpic.com/obj/im-resource/1687263122037-ts-e6999ae4b88ae5a5bd2de6989fe6989f2e706e67?lk3s=91c5b7cb&x-expires=1824552000&x-signature=VHDFJJ4fUfuEd9fAVpDtUeAYvQg%3D&from=2445653963&s=im_111&se=false&sc=image&biz_tag=aweme_im&l=20261026204156D986D598F2E909EF52D2",
    "比心": "https://p11-sign.douyinpic.com/obj/im-resource/1700709715333-ts-e6af94e5bf832e706e67?lk3s=91c5b7cb&x-expires=1824552000&x-signature=JVLqRHuTe0y4HJdAK6k%2FIPqlf1U%3D&from=2445653963&s=im_111&se=false&sc=image&biz_tag=aweme_im&l=20261026204156D986D598F2E909EF52D2",
    "早上好": "https://p9-sign.douyinpic.com/obj/im-resource/1687263059740-ts-e697a9e4b88ae5a5bd2de5a4aae998b32e706e67?lk3s=91c5b7cb&x-expires=1824552000&x-signature=KCL0Ka6rQRHhdKJHfw98IgYRaco%3D&from=2445653963&s=im_111&se=false&sc=image&biz_tag=aweme_im&l=20261026204156D986D598F2E909EF52D2",
    "早点睡": "https://p26-sign.douyinpic.com/obj/im-resource/1687263141266-ts-e6999ae4b88ae5a5bd2de697a9e782b9e79da12e706e67?lk3s=91c5b7cb&x-expires=1824552000&x-signature=jyLKCNALqzx6dyYSRTlkVTxTdqY%3D&from=2445653963&s=im_111&se=false&sc=image&biz_tag=aweme_im&l=20261026204156D986D598F2E909EF52D2",
    "在干嘛": "https://p5-ex-gddgtc-sign.douyinpic.com/obj/im-resource/1700709660537-ts-e59ca8e5b9b2e5989b2e706e67?lk3s=91c5b7cb&x-expires=1824552000&x-signature=g4IuLLbl0Brmmt%2BNyJGVR3XPfVc%3D&from=2445653963&s=im_111&se=false&sc=image&biz_tag=aweme_im&l=20261026204156D986D598F2E909EF52D2",
    "开心": "https://p26-sign.douyinpic.com/obj/im-resource/1700709744299-ts-e5bc80e5bf832e706e67?lk3s=91c5b7cb&x-expires=1824552000&x-signature=Kl5Zo7MlOC4ZcFymv%2BIlBe2uXlE%3D&from=2445653963&s=im_111&se=false&sc=image&biz_tag=aweme_im&l=20261026204156D986D598F2E909EF52D2",
    "嗨": "https://p5-ex-gddgtc-sign.douyinpic.com/obj/im-resource/1652427775960-ts-373039313837373530383930373438333137322e706e67?lk3s=91c5b7cb&x-expires=1824552000&x-signature=MjWyJ0OjcoMIDRPuEOoR2C9MSbM%3D&from=2445653963&s=im_111&se=false&sc=image&biz_tag=aweme_im&l=20261026204156D986D598F2E909EF52D2",
    "爱心": "https://p26-sign.douyinpic.com/obj/im-resource/1687263417979-ts-e788b1e5bf832e77656270?lk3s=91c5b7cb&x-expires=1824552000&x-signature=06xQlIUdU00anx%2BwW2kycF7IPTA%3D&from=2445653963&s=im_111&se=false&sc=image&biz_tag=aweme_im&l=20261026204156D986D598F2E909EF52D2",
    "绝了": "https://p26-sign.douyinpic.com/obj/im-resource/1687262734782-ts-e7bb9de4ba862e706e67?lk3s=91c5b7cb&x-expires=1824552000&x-signature=oSeuQCF8MhTCIW3aZifX2OH68nQ%3D&from=2445653963&s=im_111&se=false&sc=image&biz_tag=aweme_im&l=20261026204156D986D598F2E909EF52D2",
    "笑死": "https://p11-sign.douyinpic.com/obj/im-resource/1700709792873-ts-e7ac91e593ad2e706e67?lk3s=91c5b7cb&x-expires=1824552000&x-signature=ACmBMwQsYIhvTfxJAgbF7cwDMl8%3D&from=2445653963&s=im_111&se=false&sc=image&biz_tag=aweme_im&l=20261026204156D986D598F2E909EF52D2",
    "已阅": "https://p26-sign.douyinpic.com/obj/im-resource/1687262804182-ts-e5b7b2e998852e706e67?lk3s=91c5b7cb&x-expires=1824552000&x-signature=HGhHgSG4rwLUS5NqIzjxyD3fOUA%3D&from=2445653963&s=im_111&se=false&sc=image&biz_tag=aweme_im&l=20261026204156D986D598F2E909EF52D2",
}
for name, url in STICKERS.items():
    with urlopen(url, timeout=30) as response:
        data = response.read()
    (OUTPUT / f"{name}.png").write_bytes(data)
    print(name, len(data))
