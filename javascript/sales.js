var generate_sales = function(years, cost_data, weight_data) {
  var all_data = {
    cost: {
      labels: years,
      datasets: [
        {
          label: 'USD (Millions)',
          data: cost_data,
          fillColor: 'rgba(150,200,180,0.2)',
          pointColor: 'rgba(150,200,180,1)',
          strokeColor: 'rgba(150,200,180,1)',
          pointHighlightFill: 'rgba(204,0,0,1)'
        }
      ]
    },

    weight: {
      labels: years,
      datasets: [
        {
          label: 'Metric tonnes',
          data: weight_data,
          fillColor: 'rgba(150,150,150,0.2)',
          pointColor: 'rgba(150,150,150,1)',
          strokeColor: 'rgba(150,150,150,1)',
          pointHighlightFill: 'rgba(204,0,0,1)'
        }
      ]
    }
  };

  var article = document.getElementById('sales');

  for (var set in all_data) {
    var canvas = document.getElementById(set+'-graph');
    var ctx = canvas.getContext('2d');
    var data = all_data[set];
    var chart = new Chart(ctx).Line(data);
    console.log(canvas, ctx, data, chart);
  }
};

