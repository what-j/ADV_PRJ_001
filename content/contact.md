---
title: お問い合わせ
author: ファルコン速報編集部
draft:
---

ファルコン速報に関するご質問、お問い合わせ、提案、ご意見、報道に関する情報など、どんなご連絡でもお気軽にご寄せください。

1. ## お問い合わせフォーム

    必要事項をご記入いただきましたら、送信ボタンを押してください。

    **お問い合わせフォーム**

    <div class="contact-form" enctype="multipart/form-data" style="width: 100; margin: auto;">
        <form action="/contact_sucess" name="contact" method="POST" id="contact-form" netlify>
            <div style="display: none;"><input type="text" name="trap" /></div>
            <label for="name">お名前:</label><br>
            <input type="text" id="name" name="name" required><br><br>
            <label for="email">メールアドレス:</label><br>
            <input type="email" id="email" name="email" required><br><br>
            <label for="message">お問い合わせ内容:</label><br>
            <textarea id="message" name="message" rows="4" required></textarea><br><br>
            <input type="file" name="参考資料" />
            <input type="submit" value="送信">
        </form>
    </div>


    <script src="https://www.google.com/recaptcha/api.js"></script>
    <script>
        document.getElementById("contact-form").addEventListener("submit", function (event) {
            event.preventDefault();
            const formData = new FormData(event.target);
            const formDataJson = {};
            formData.forEach((value, key) => {
                formDataJson[key] = value;
            });

            fetch("/submit", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify(formDataJson)
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    alert("お問い合わせが送信されました。");
                } else {
                    alert("お問い合わせの送信中にエラーが発生しました。もう一度お試しください。");
                }
            })
            .catch(error => {
                console.error("エラーが発生しました: " + error.message);
                alert("お問い合わせの送信中にエラーが発生しました。もう一度お試しください。");
            });
        });
    </script>

    お問い合わせフォームからの送信後、運営からの返信をお待ちください。ご質問やお問い合わせ内容に応じて、適切な対応をさせていただきます。

