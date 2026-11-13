(function () {
  "use strict";
  var list = document.getElementById("category-setting-list");
  var hidden = document.getElementById("categories-value");
  var form = document.getElementById("settings-form");
  if (!list || !hidden || !form) return;
  function bindRemove(button) {
    button.addEventListener("click", function () { button.closest(".category-setting-row").remove(); });
  }
  function add(value) {
    var row = document.createElement("div");
    row.className = "category-setting-row";
    var input = document.createElement("input");
    input.className = "category-setting-input";
    input.maxLength = 80;
    input.value = value || "";
    input.setAttribute("aria-label", "Kategori adı");
    var button = document.createElement("button");
    button.type = "button";
    button.className = "button ghost category-remove";
    button.textContent = "Sil";
    bindRemove(button);
    row.append(input, button);
    list.appendChild(row);
    input.focus();
  }
  list.querySelectorAll(".category-remove").forEach(bindRemove);
  document.getElementById("category-add").addEventListener("click", function () { add(""); });
  form.addEventListener("submit", function () {
    hidden.value = Array.from(list.querySelectorAll(".category-setting-input"))
      .map(function (input) { return input.value.trim(); })
      .filter(Boolean).filter(function (value, index, values) { return values.indexOf(value) === index; })
      .join(", ");
  });
})();
