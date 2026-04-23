"""Offline answers when OpenAI is not configured or fails. Bilingual EN / MR."""
from __future__ import annotations

import re


def _extract_fat_percent(text: str) -> float | None:
    t = text.lower().replace(",", ".")
    for pattern in (
        r"fat\s*[:\-]?\s*(\d+\.?\d*)",
        r"(\d+\.?\d*)\s*%?\s*(?:fat|snf)",
        r"फॅट\s*[:\-]?\s*(\d+\.?\d*)",
        r"(\d+\.?\d*)\s*%?\s*फॅट",
    ):
        m = re.search(pattern, t, re.I)
        if m:
            try:
                return float(m.group(1))
            except ValueError:
                continue
    return None


def _mentions_cow(text: str) -> bool:
    t = text.lower()
    return "cow" in t or "गाय" in text or "दूध" in text


def _mentions_buffalo(text: str) -> bool:
    t = text.lower()
    return "buffalo" in t or "म्हैस" in text or "भैंस" in text


def local_farmer_reply(message: str, lang: str) -> str | None:
    """
    Return a helpful fixed answer for common questions, or None to use generic fallback.
    """
    raw = message.strip()
    if not raw:
        return None

    t = raw.lower()
    fat_val = _extract_fat_percent(raw)
    fat_topic = bool(re.search(r"fat|फॅट|snf", raw, re.I)) or fat_val is not None

    if fat_topic and fat_val is not None:
        if lang == "mr":
            cow = _mentions_cow(raw) or not _mentions_buffalo(raw)
            if cow:
                return (
                    f"{fat_val}% फॅट हे गायीच्या दूधासाठी सामान्यतः कमी बाजूला असू शकते; "
                    "बहुतेक वेळा गायीच्या दूधात सुमारे ३.५ ते ५% फॅट दिसते, पण जात, वय, "
                    "विभाग, आहार आणि दूध काढल्यानंतरच्या वेळेनुसार फरक पडतो. "
                    "२.३% ‘अवैध’ नसते, पण तुमच्या दूध संघाने खरेदीसाठी किमान फॅट/SNF ठरवलेले असू शकते — "
                    "ते कार्यालयात विचारा. अचानक फॅट कमी झाल्यास पशुवैद्यकीय सल्ला घ्या."
                )
            return (
                f"{fat_val}% फॅट म्हैसीच्या दूधाशी तुलना केल्यास वेगळे मानदंड लागू होतात; "
                "संघाचे नियम आणि चाचणी पद्धत तपासा. शंका असल्यास पशुवैद्यक किंवा पशुपालन विभागाशी संपर्क साधा."
            )

        cow = _mentions_cow(raw) or not _mentions_buffalo(raw)
        if cow:
            return (
                f"{fat_val}% fat for cow milk can be on the lower side; many cows often test around "
                "roughly 3.5-5% depending on breed, days in milk, feed, and sampling. "
                'It is not automatically "invalid," but your dairy union may have minimum fat/SNF rules '
                "for purchase - ask at the collection center. If fat dropped suddenly, speak with a "
                "veterinarian about feed and animal health."
            )
        return (
            f"{fat_val}% fat means different things for buffalo versus cow milk. "
            "Check your society's testing method and minimum standards. "
            "If something changed sharply, consult a veterinarian or livestock officer."
        )

    if fat_topic and fat_val is None:
        if lang == "mr":
            return (
                "फॅट टक्केवारी जात, आहार, लॅक्टेशनचा टप्पा आणि नमुना काढण्याच्या पद्धतीवर अवलंबून असते. "
                "तुमच्या दूध संघाचे किमान नियम कार्यालयात विचारा. "
                "अचानक बदल झाल्यास पशुवैद्यकीय तपासणी करा."
            )
        return (
            "Fat percentage depends on breed, feed, stage of lactation, and how the sample is tested. "
            "Ask your dairy for their minimum fat/SNF rules. If readings changed suddenly, "
            "check animal health and feeding with a veterinarian."
        )

    pay = re.search(r"payment|pay|money|amount|बिल|पैसे|रक्कम|देयक", t)
    if pay:
        if lang == "mr":
            return (
                "दूध दर आणि देयक तुमच्या संघाच्या दरपत्रकावर अवलंबून असते. "
                "तुमच्या खात्याचा तपशील दूध केंद्र किंवा कार्यालयातून विचारा."
            )
        return (
            "Milk price and payments follow your cooperative’s rate chart and deductions. "
            "Ask your collection center or office for your account statement."
        )

    if re.search(r"^hi\b|^hello\b|नमस्कार|नमस्ते", t):
        if lang == "mr":
            return "नमस्कार! दूध, फॅट, दर किंवा प्राणी निगा याबद्दल प्रश्न विचारा."
        return "Hello! Ask about milk quality, fat %, payments, or general dairy tips."

    return None


def generic_assistant_reply(lang: str) -> str:
    """Used when no API key and no specific local match."""
    if lang == "mr":
        return (
            "या मदतीसाठी पूर्ण AI जोडणी आवश्यक असेल किंवा प्रश्न अधिक विशिष्ट असावा. "
            "दूध फॅट, दर आणि नोंदींबाबत थेट तुमच्या दूध केंद्राशी संपर्क साधा. "
            "सामान्य माहिती: गायीच्या दूधात फॅट बहुधा ३.५–५% दिसतो, पण फरक पडू शकतो; "
            "संघाचे किमान नियम नेहमी तपासा."
        )
    return (
        "I can answer simple dairy questions here. For account-specific amounts or society rules, "
        "ask your dairy collection center. In general, cow milk fat often falls around roughly 3.5–5% "
        "but varies by animal and feed; your union sets purchase standards."
    )
