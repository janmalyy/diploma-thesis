document.addEventListener("DOMContentLoaded", function () {
  const input = document.getElementById("query-input");
  const button = document.getElementById("run-query");

  button.addEventListener("click", () => {
    const query = input.value;
    if (!query.trim()) return; // if the input is empty, stop here

    fetch("/api/query", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: query })
    })
      .then(res => {
        if (!res.ok) {
          return res.json().then(err => {
            const errorMsg = err.detail || 'Unknown error';
            throw new Error(`Error: ${errorMsg}`);
          });
        }
        return res.json();
      })
      .then(data => {
        // Clear any previous error messages
        const errorDiv = document.getElementById('error-message');
        if (errorDiv) errorDiv.remove();

        // Process successful response
        const elements = [...data.nodes, ...data.edges];
        cytoscape({
          container: document.getElementById("cy"),
          elements: elements,
          style: [
            { selector: "node", style: { "label": "data(label)", "background-color": "#0074D9" }},
            { selector: "edge", style: { "label": "data(label)", "line-color": "#ccc", "target-arrow-shape": "triangle" }}
          ],
          layout: { name: "cose" }
        });
      })
      .catch(error => {
        console.error(error);

        // Display error to user
        const queryContainer = document.getElementById('query-container');
        let errorDiv = document.getElementById('error-message');

        if (!errorDiv) {
          errorDiv = document.createElement('div');
          errorDiv.id = 'error-message';
          errorDiv.style.color = 'red';
          errorDiv.style.marginTop = '10px';
          queryContainer.after(errorDiv);
        }

        errorDiv.textContent = error.message;
      });
  });
});
