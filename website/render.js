  
  var markers = [];
  var infowindows = []

  var current_IXP = "None"
  var current_AS = "ALL"


  function createMarkersRemotePeers(map, infowindow, ixp_name){
    markers[ixp_name] = []
    infowindows[ixp_name] = []
    
    var i = 0
    do {

      //TODO: display proper icon 
    
    var obj = data[ixp_name][i];
    var marker = new google.maps.Marker({
      map: map,
      position: {lat: Number(obj.lat), lng: Number(obj.lon)},
      title: obj.asn,
      icon: "./icon/tiny.png"
    });

    marker.setVisible(false)

    if(!markers[ixp_name][obj.asn]) markers[ixp_name][obj.asn] = []
    markers[ixp_name][obj.asn].push( { key: i , value: marker } );

    if(!infowindows[ixp_name][obj.asn]) infowindows[ixp_name][obj.asn] = []

    infowindows[ixp_name][i] = 'Remote Peering ASN: <b>' + obj.asn + '</b></br>' 
                      + 'Location: <b>' + obj.city + '</b></br>'           
                      + 'Router IP: <b>' + obj.ip + '</b></br>'
                      + 'Median RTT: <b>' + obj.median_rtt + '</b></br>'
                      + '</br>Details about <b>AS' + obj.asn + '</b> on RIPEstat <a href="https://stat.ripe.net/' 
                      + obj.asn + '#tabId=at-a-glance" target="_blank"><b>here</b></a>';

  
    google.maps.event.addListener(marker, 'click', (function(marker, i) {
      return function() {
        infowindow.setContent(infowindows[ixp_name][i]);
        infowindow.open(map, marker);
      }
     })(marker, i));

    i++;

    }while (i < data[ixp_name].length);

  }

  function createMarkersIXPS(map, infowindow, ixp_name){
    var i = 0;
    infowindow[ixp_name] = []
    markers[ixp_name] = []
    do {
        
      var obj = data[ixp_name][i];
      var id = obj.id;

      var marker = new google.maps.Marker({
        map: map,
        position: obj.coordinates,
        title: obj.id,
        icon: obj.image
      });
      marker.setVisible(false)
      
      markers[ixp_name][id] = marker;
      
      infowindow[ixp_name][i] = 'IXP: <b>' + obj.id + '</b></br>' 
                        + 'Location: <b>' + obj.location + '</b></br>';            

        google.maps.event.addListener(marker, 'click', (function(marker, i) {
          return function() {
            infowindow.setContent(infowindow[ixp_name][i]);
            infowindow.open(map, marker);
          }
         })(marker, i));

        i++;
    
      }while (i < data[ixp_name].length);
  }

  function initMap() {

    var mapDiv = document.getElementById('map');
    var map = new google.maps.Map(mapDiv, {
        center: {lat: 17.5500311, lng: 6.2732165},
        zoom: 3,
        streetViewControl: false
    });

    var i = 0;

    var markers = [];
    var infowindow = new google.maps.InfoWindow();

    console.log(data)
    createMarkersIXPS(map, infowindow, "IXPS-LIST")

    createMarkersRemotePeers(map, infowindow, "DE-CIX")
    createMarkersRemotePeers(map, infowindow, "LINX")
    createMarkersRemotePeers(map, infowindow, "AMS-IX")
    createMarkersRemotePeers(map, infowindow, "ANY2")
    createMarkersRemotePeers(map, infowindow, "FRANCE-IX")
    createMarkersRemotePeers(map, infowindow, "MSK-IX")


    var legend = document.getElementById('legend');
    
    var div = document.createElement('div');
    div.id = "selectIXP"
    div.innerHTML = '</br><b>Display Remote Peerings:</b> </br></br><center><select onchange=\"report(this.value)\">'
                     + ' <option value="None">None</option>'
                     + ' <option value="AMS-IX">AMS-IX</option>'
                     + ' <option value="DE-CIX">DE-CIX</option>'
                     + ' <option value="FRANCE-IX">France-IX</option>'
                     + ' <option value="LINX">LINX</option>'
                     + ' <option value="ANY2">ANY2</option>'
                     + ' <option value="MSK-IX">MSK-IX</option>'
                    + '</select></center> ';
    
    legend.appendChild(div);

    var div = document.createElement('div');
    div.id = "selectAS"
    div.innerHTML = "</br>"
    legend.appendChild(div);

    map.controls[google.maps.ControlPosition.RIGHT_TOP].push(legend);

    var footer = document.getElementById('footer');
    var footerdiv = document.createElement('div');
    footerdiv.id = "footerLastUpdate"
    footerdiv.innerHTML = "<b>Last Updated: 1/12/2016</b>"

    footer.appendChild(footerdiv)

    map.controls[google.maps.ControlPosition.BOTTOM_CENTER].push(footer);

  }

  function update_per_IXP(){

    var select_AS = document.getElementById('selectAS');
    var tmp = ""

    if(current_IXP != "None"){
      
      for ( i in markers[current_IXP] ){
        tmp += '<option value="' + i + '"> AS' + i + ' (' + Object.keys(markers[current_IXP][i]).length + ')</option>'
      }

      select_AS.innerHTML = '<hr></hr><b> Display for specific AS: </b></br></br> <center><select onchange=\"report_AS(this.value)\">'
                          + '<option value="ALL">All (' + Object.keys(markers[current_IXP]).length + ')</option>' 
                          + tmp + '</select></center></br>'

    }else{
      select_AS.innerHTML = ''
    }
  
  }

  function report_AS(ASN){

    handleMarkers(current_IXP, current_AS , false) //hide
    handleMarkers(current_IXP, ASN, true) //show
    current_AS = ASN

  }
      
  function report(ixp_name){

    if(ixp_name == "None"){
      handleMarkers(current_IXP, current_AS, false) // hide
      current_IXP = ixp_name
    }else{ 
      handleMarkers(current_IXP, "ALL", false) // hide
      current_IXP = ixp_name
      handleMarkers(current_IXP, "ALL") // show
      current_AS = "ALL"
    }
    update_per_IXP()
  }

  function handleMarkers(ixp_name, ASN, show_hide){

    if(ASN == "ALL"){
      for(var i_asn in markers[ixp_name]){
        for (var i in markers[ixp_name][i_asn]){
          markers[ixp_name][i_asn][i].value.setVisible(show_hide)
        }
      }
    }else{
      for (var i in markers[ixp_name][ASN]){
          markers[ixp_name][ASN][i].value.setVisible(show_hide)
        }
    }
    if(ixp_name!= "None") markers["IXPS-LIST"][ixp_name].setVisible(show_hide)
    return
  }

