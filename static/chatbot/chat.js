/* Chat rag-app : envoi de question, lecture du flux SSE, rendu sûr du DOM.
 * Règle XSS : tout texte venant du LLM passe par textContent, jamais innerHTML.
 */
(function () {
    "use strict";

    var chat = document.getElementById("chat");
    if (!chat) return;

    var composer = document.getElementById("composer");
    var input = document.getElementById("question-input");
    var sendButton = document.getElementById("send-btn");
    var messagesBox = document.getElementById("messages");
    var streamingEnabled = chat.dataset.streaming === "1";
    var sendUrl = chat.dataset.sendUrl;

    // HTMX : confirmation avant suppression (les routes DELETE/POST sont protégées).
    document.body.addEventListener("htmx:confirm", function (event) {
        if (event.detail.path && event.detail.path.includes("/delete/")) {
            event.preventDefault();
            if (window.confirm(event.detail.elt.getAttribute("hx-confirm") || "Confirmer ?")) {
                event.detail.issueRequest();
            }
        }
    });

    if (!composer) return;

    composer.addEventListener("submit", function (event) {
        event.preventDefault();
        var question = input.value.trim();
        if (!question) return;

        var userBubble = bubble("user");
        userBubble.querySelector(".content").textContent = question;
        messagesBox.appendChild(userBubble);

        var assistantBubble = bubble("assistant");
        var contentSpan = assistantBubble.querySelector(".content");
        messagesBox.appendChild(assistantBubble);
        scrollToBottom();

        setBusy(true);

        if (!streamingEnabled || !window.ReadableStream) {
            // Mode non streamé : le serveur renvoie le fragment HTML du message.
            postForm(sendUrl, { question: question })
                .then(function (html) {
                    var wrapper = document.createElement("div");
                    wrapper.innerHTML = html; // fragment rendu par Django (échappé)
                    assistantBubble.replaceWith(wrapper.firstElementChild);
                    scrollToBottom();
                })
                .catch(showError)
                .finally(function () {
                    setBusy(false);
                });
            return;
        }

        streamAnswer(sendUrl, question, assistantBubble, contentSpan);
    });

    /** Consomme le flux SSE via fetch (POST + CSRF) et ReadableStream. */
    function streamAnswer(url, question, assistantBubble, contentSpan) {
        var csrf = chat.dataset.csrf;
        fetch(url, {
            method: "POST",
            headers: {
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                "X-CSRFToken": csrf,
            },
            body: new URLSearchParams({ question: question }).toString(),
        })
            .then(function (response) {
                if (!response.ok || !response.body) {
                    throw new Error("HTTP " + response.status);
                }
                readSse(response.body, {
                    sources: function (data) {
                        assistantBubble.appendChild(buildSources(data));
                        scrollToBottom();
                    },
                    token: function (data) {
                        contentSpan.textContent += data.t;
                        scrollToBottom();
                    },
                    error: function (data) {
                        showError(new Error(data.message || "Erreur"));
                    },
                    done: function () {
                        setBusy(false);
                        input.focus();
                    },
                });
            })
            .catch(function (error) {
                showError(error);
                setBusy(false);
            });
    }

    /** Analyse le flux : découpe par événements SSE séparés par une ligne vide. */
    function readSse(body, handlers) {
        var reader = body.getReader();
        var decoder = new TextDecoder();
        var buffer = "";

        function pump() {
            return reader.read().then(function (result) {
                if (result.done) return;
                buffer += decoder.decode(result.value, { stream: true });
                var parts = buffer.split("\n\n");
                buffer = parts.pop();
                parts.forEach(function (raw) {
                    dispatchEvent(raw, handlers);
                });
                return pump();
            });
        }
        pump();
    }

    function dispatchEvent(raw, handlers) {
        var eventName = "message";
        var data = "";
        raw.split("\n").forEach(function (line) {
            if (line.indexOf("event: ") === 0) eventName = line.slice(7).trim();
            if (line.indexOf("data: ") === 0) data += line.slice(6);
        });
        if (!data) return;
        try {
            var payload = JSON.parse(data);
            if (handlers[eventName]) handlers[eventName](payload);
        } catch (error) {
            console.error("SSE illisible", error);
        }
    }

    // --- Helpers DOM ---------------------------------------------------------

    function bubble(role) {
        var element = document.createElement("div");
        element.className = "message " + role;
        var content = document.createElement("div");
        content.className = "content";
        element.appendChild(content);
        var empty = document.getElementById("empty-state");
        if (empty) empty.remove();
        return element;
    }

    /** Sources rendues sans innerHTML : pas d'injection possible. */
    function buildSources(sources) {
        var details = document.createElement("details");
        details.className = "sources";
        var summary = document.createElement("summary");
        summary.textContent = "Sources (" + sources.length + ")";
        details.appendChild(summary);
        var list = document.createElement("ul");
        sources.forEach(function (source) {
            var item = document.createElement("li");
            var title = document.createElement("strong");
            title.textContent = source.source;
            item.appendChild(title);
            if (source.page !== null && source.page !== undefined) {
                item.appendChild(document.createTextNode(", page " + source.page));
            }
            var score = document.createElement("span");
            score.className = "score";
            score.textContent = "score " + Number(source.score).toFixed(3);
            item.appendChild(score);
            item.appendChild(document.createElement("br"));
            var excerpt = document.createElement("em");
            excerpt.textContent = source.excerpt || "";
            item.appendChild(excerpt);
            list.appendChild(item);
        });
        details.appendChild(list);
        return details;
    }

    function showError(error) {
        var banner = document.createElement("p");
        banner.className = "error-banner";
        banner.textContent = "Erreur : " + error.message;
        messagesBox.appendChild(banner);
        scrollToBottom();
    }

    function setBusy(busy) {
        input.disabled = busy;
        sendButton.disabled = busy;
        if (!busy) input.focus();
    }

    function scrollToBottom() {
        messagesBox.scrollTop = messagesBox.scrollHeight;
    }

    /** POST formulaire classique (mode non streamé), renvoie le texte HTML. */
    function postForm(url, fields) {
        var csrf = chat.dataset.csrf;
        var body = new URLSearchParams(fields).toString();
        return fetch(url, {
            method: "POST",
            headers: {
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                "X-CSRFToken": csrf,
            },
            body: body,
        }).then(function (response) {
            if (!response.ok) throw new Error("HTTP " + response.status);
            return response.text();
        });
    }
})();
