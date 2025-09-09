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
      .then(res => res.json())
      .then(data => {
        const elements = [...data.nodes, ...data.edges];
        cytoscape({
          container: document.getElementById("cy"), // where on the page to put the graph (the element with ID "cy")
          elements: elements, // what to draw (nodes + edges)
          style: [
            { selector: "node", style: { "label": "data(label)", "background-color": "#0074D9" }},
            { selector: "edge", style: { "label": "data(label)", "line-color": "#ccc", "target-arrow-shape": "triangle" }}
          ],
          layout: { name: "cose" }  // "cose" makes the nodes spread out in a balanced way.
        });
      });
  });
});
