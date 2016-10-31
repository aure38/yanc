function ProgressTimer() {
    $('#check_progress_bar')[0].setAttribute("style", "width:"+gv_progresstimer+"%") ;
    gv_progresstimer = gv_progresstimer + 1 ;
    if ( gv_progresstimer >= 98 ) {
        clearInterval(gv_progressVariable) ;
    }
}

function reloadimagefeed() {
    $('#feed_image_thumb')[0].setAttribute("src", $('#feed_image_url')[0].value) ;
}

function subscribe2feed() {
    $('#button_subscribe')[0].setAttribute("disabled", "True") ;
    $.getJSON(url="./abonn2feed", data={"usrun":gv_un , "feedid":$('#feed_id')[0].value, "feedurl":$('#feed_url')[0].value, "feedname":$('#feed_name')[0].value, "feeddescription":$('#feed_description')[0].value, "image_url":$('#feed_image_url')[0].value}, success=function( data13 )
    {
        $('#feedshow')[0].innerHTML = JSON.stringify(data13,undefined, 2) ;
    }) ;
}

function checkURL(theURL) {
    $('#feedshow')[0].innerHTML = "" ;

    $('#feed_name')[0].value = "" ;
    $('#feed_name')[0].setAttribute("disabled", "True") ;

    $('#feed_description')[0].value = "" ;
    $('#feed_description')[0].setAttribute("disabled", "True") ;

    $('#feed_image_url')[0].value = "";
    $('#feed_image_url')[0].setAttribute("disabled", "True") ;
    $('#image_reload')[0].setAttribute("disabled", "True") ;
    $('#feed_image_thumb')[0].setAttribute("src", "") ;
    $('#feed_image_thumb')[0].setAttribute("hidden", "True") ;

    $('#feed_id')[0].value = "" ;
    $('#button_subscribe')[0].setAttribute("disabled", "True") ;

    gv_progresstimer = 20 ;
    gv_progressVariable = setInterval(ProgressTimer, 500) ;


    $('#check_progress_div')[0].removeAttribute("hidden") ;
    $('#check_progress_text')[0].innerHTML = "Querying + Parsing"

    $.getJSON(url="./feedcheck1", data={"usrun":gv_un , "feedurl":theURL}, success=function( data11 )
    {
        clearInterval(gv_progressVariable) ;
        $('#check_progress_bar')[0].setAttribute("style", "width:100%") ;
        $('#feedshow')[0].innerHTML += '<br>' + JSON.stringify(data11,undefined, 2) ;

        if ( data11['status'] == 'oknew' ) {
            $('#check_progress_bar')[0].setAttribute("class", "progress-bar progress-bar-success") ;
            $('#check_progress_text')[0].innerHTML = "Feed Parsed OK"

            $('#feed_name')[0].value = data11['feedobj']['headers']['name'] ;
            $('#feed_name')[0].removeAttribute("disabled") ;

            $('#feed_description')[0].value = data11['feedobj']['headers']['description'] ;
            $('#feed_description')[0].removeAttribute("disabled") ;

            $('#feed_image_url')[0].value = data11['feedobj']['headers']['image_url_online'] ;
            $('#feed_image_url')[0].removeAttribute("disabled") ;
            $('#image_reload')[0].removeAttribute("disabled") ;

            $('#feed_image_thumb')[0].setAttribute("src", data11['feedobj']['headers']['image_url_online']) ;
            $('#feed_image_thumb')[0].removeAttribute("hidden") ;

            $('#feed_id')[0].value = data11['feedobj']['id'] ;
            $('#button_subscribe')[0].removeAttribute("disabled") ;
        }
        else if ( data11['status'] == 'okdb' ) {
            $('#check_progress_bar')[0].setAttribute("class", "progress-bar progress-bar-success") ;
            $('#check_progress_text')[0].innerHTML = "Feed identified OK"
        }
        else {
            $('#check_progress_bar')[0].setAttribute("class", "progress-bar progress-bar-danger") ;
            $('#check_progress_text')[0].innerHTML = "Error during parsing"
        }
    }) ;
}

// --- Quand la page HTML est prete
$(document).ready(function() {

    // -- Init
    gv_un = undefined
    gv_un1 = location.search.split('usrun=')[1] ;
    if ( gv_un1 ) {
        gv_un = gv_un1.split('&')[0] ;
    }
    if ( gv_un == undefined ) {
        gv_un = localStorage.getItem('gv_un') ;
        if ( gv_un == undefined ) {
            gv_un = '-' ;
        }
    }
    else {
        localStorage.setItem('gv_un', gv_un)
    }
    $('#fd_un')[0].innerHTML = gv_un

} ) ;
