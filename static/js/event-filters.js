(function () {
    "use strict";

    const unspecified = "__unspecified__";

    function matchesEvent(event, filters) {
        const location = event.location || unspecified;
        const type = event.type || unspecified;
        const lastDate = event.endDate || event.date;
        return (!filters.location || filters.location === location) &&
            (!filters.type || filters.type === type) &&
            (!filters.from || lastDate >= filters.from) &&
            (!filters.to || event.date <= filters.to);
    }

    function addOptions(select, rows, key, labelKey, document) {
        const options = new Map();
        rows.forEach(function (row) {
            const value = row.dataset[key] || unspecified;
            options.set(value, row.dataset[labelKey] || "Non specificato");
        });
        Array.from(options).sort(function (left, right) {
            return left[1].localeCompare(right[1], "it", { sensitivity: "base" });
        }).forEach(function (option) {
            const element = document.createElement("option");
            element.value = option[0];
            element.textContent = option[1];
            select.appendChild(element);
        });
    }

    function initialize(document) {
        const form = document.getElementById("event-filters");
        const results = document.getElementById("event-results");
        if (!form || !results) return;
        const rows = Array.from(results.querySelectorAll("[data-event]"));
        if (!rows.length) return;

        const location = document.getElementById("event-location");
        const type = document.getElementById("event-type");
        const from = document.getElementById("event-from");
        const to = document.getElementById("event-to");
        const count = document.getElementById("event-filter-count");
        const empty = document.getElementById("event-filter-empty");
        const error = document.getElementById("event-filter-error");
        const groups = Array.from(results.querySelectorAll("[data-event-group]"));

        addOptions(location, rows, "location", "locationLabel", document);
        addOptions(type, rows, "type", "typeLabel", document);

        function render() {
            const filters = { location: location.value, type: type.value, from: from.value, to: to.value };
            const invalid = Boolean(filters.from && filters.to && filters.from > filters.to);
            to.setCustomValidity(invalid ? "La data finale precede quella iniziale." : "");
            to.setAttribute("aria-invalid", String(invalid));
            error.hidden = !invalid;
            let visible = 0;
            rows.forEach(function (row) {
                row.hidden = invalid || !matchesEvent(row.dataset, filters);
                if (!row.hidden) visible += 1;
            });
            groups.forEach(function (group) {
                group.hidden = !Array.from(group.querySelectorAll("[data-event]")).some(function (row) {
                    return !row.hidden;
                });
            });
            count.textContent = invalid ? "Controlla l’intervallo di date." :
                visible + (visible === 1 ? " evento" : " eventi") + " su " + rows.length;
            empty.hidden = invalid || visible > 0;
        }

        form.addEventListener("input", render);
        form.addEventListener("change", render);
        form.addEventListener("submit", function (event) { event.preventDefault(); });
        document.getElementById("event-reset").addEventListener("click", function () {
            form.reset();
            render();
        });
        form.hidden = false;
        count.hidden = false;
        render();
    }

    if (typeof module !== "undefined" && module.exports) {
        module.exports = { matchesEvent: matchesEvent, initialize: initialize };
    }
    if (typeof document !== "undefined") {
        if (document.readyState === "loading") {
            document.addEventListener("DOMContentLoaded", function () { initialize(document); });
        } else {
            initialize(document);
        }
    }
}());
