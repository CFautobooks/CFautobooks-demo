console.log('CF AutoBooks Modern v6 loaded');

// OCR integration for invoice upload
document.addEventListener("DOMContentLoaded", () => {
  const uploadBtn = document.getElementById("uploadBtn");
  const fileInput = document.getElementById("invoiceFile");
  const resultDiv = document.getElementById("ocrResult");
  const lineItemsBody = document.getElementById("lineItemsBody");

  // Replace with your actual API base URL
  const OCR_API_URL = "https://api.cfautobooks.com.au/api/ocr";

  if (uploadBtn && fileInput && resultDiv && lineItemsBody) {
    uploadBtn.addEventListener(\"click\", async () => {
    // Check if user is logged in
    const token = localStorage.getItem("authToken");
    if (!token) {
      alert("Please log in or sign up to upload invoices.");
      window.location.href = "login.html";
      return;
    }

      if (!fileInput.files.length) {
        alert("Please select a file first.");
        return;
      }

      const file = fileInput.files[0];
      const formData = new FormData();
      formData.append("file", file);

      uploadBtn.disabled = true;
      uploadBtn.textContent = "Processing…";

      try {
        const resp = await fetch(OCR_API_URL, {
          method: "POST",
          body: formData
        });
        if (!resp.ok) {
          const err = await resp.json();
          throw new Error(err.detail || "OCR service error");
        }
        const data = await resp.json();
        displayOCRResults(data);
      } catch (e) {
        console.error("OCR error:", e);
        alert("Failed to process invoice: " + e.message);
      }

      uploadBtn.disabled = false;
      uploadBtn.textContent = "Upload & Process";
    });
  }

  function displayOCRResults(data) {
    resultDiv.style.display = "block";
    lineItemsBody.innerHTML = "";

    data.line_items.forEach(item => {
      const row = document.createElement("tr");

      const descCell = document.createElement("td");
      descCell.style.border = "1px solid #ccc";
      descCell.style.padding = "8px";
      descCell.textContent = item.description;
      row.appendChild(descCell);

      const amtCell = document.createElement("td");
      amtCell.style.border = "1px solid #ccc";
      amtCell.style.padding = "8px";
      amtCell.textContent = item.amount.toFixed(2);
      row.appendChild(amtCell);

      const catCell = document.createElement("td");
      catCell.style.border = "1px solid #ccc";
      catCell.style.padding = "8px";
      catCell.textContent = item.category;
      row.appendChild(catCell);

      const confCell = document.createElement("td");
      confCell.style.border = "1px solid #ccc";
      confCell.style.padding = "8px";
      confCell.textContent = (item.confidence * 100).toFixed(0) + "%";
      row.appendChild(confCell);

      const revCell = document.createElement("td");
      revCell.style.border = "1px solid #ccc";
      revCell.style.padding = "8px";
      revCell.textContent = item.requires_review ? "Yes" : "No";
      row.appendChild(revCell);

      lineItemsBody.appendChild(row);
    });
  }
});
