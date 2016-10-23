function deleteArticle(rowID, theID)
{
    // -- Effacement de la ligne dans la table HTML
    document.getElementById(rowID).remove() ;

    // -- Requete pour tag DEL dans la BD
    $.getJSON(url="./dartic", data={"usrun":gv_un , "artid":theID}, success=function( data2 )
    {
        if ( gv_nbartic > 0 ) {
            gv_nbartic = gv_nbartic-1 ;
            gv_nbartictotal = gv_nbartictotal-1 ;
            updateNbArtic() ;
        }
    }) ;
}

function updateNbArtic()
{
    $('#fd_nbartic')[0].innerHTML = gv_nbartic + " on " + gv_nbartictotal ;
}

function fillGUI(articles)
{
    // -- Boucle sur les articles a afficher
    var tbl = document.getElementById('tblarticles') ;
    for (var i = 0, len = articles.length; i < len; i++) {
        article = articles[i] ;
        var new_row = tbl.firstElementChild.cloneNode(true) ;
        var row_id = "ligne-"+article['id'] ;
        new_row.setAttribute("id", row_id);
        var new_row_children = new_row.children ;

        var tex_col1 = article['date'] + '&nbsp;&nbsp;<span class="badge">' + article['score'] + '</span><br>' + article['tags'] ;

        var tex_col2 = '' ; // '<div style="position:relative;">' ;
        tex_col2 = tex_col2 + '<a href="' + article['url'] + '" target="_blank"><img src="' + article['image'] + '" class="img-rounded" style="height:70px;max-width:90px;"/></a>' ; // max-height:80px; width:100%;

        var tex_col3 = '' ; // '<div style="position:relative;">' ;
        tex_col3 = tex_col3 + '<div style="font-size: 130%;"><b>' + article['title'] + '</b></div>' + article['summary'] ;

        var tex_col4 = '<div class="btn-toolbar" role="toolbar" style:"margin:0px;">' ;
        tex_col4 = tex_col4 + '<div class="btn btn-block btn-xs btn-danger" style="width:40px; margin: 0px; margin-right:4px;" onclick="deleteArticle(\''+row_id+'\', \'' + article['id'] + '\')">DEL</div>' ;
        tex_col4 = tex_col4 + '<a class="btn btn-block btn-xs btn-success" style="width:50px; margin: 0px; margin-right:4px;" href="' + article['url'] + '" target="_blank">OPEN</a>' ;
        tex_col4 = tex_col4 + '<div class="btn btn-block btn-xs btn-primary" style="width:50px; margin: 0px;" onclick="deleteArticle(\''+row_id+'\', \'' + article['id'] + '\')">SAVE</div>' ;
        tex_col4 = tex_col4 + '</div>' ;

        new_row_children[0].innerHTML = tex_col1 ;
        new_row_children[1].innerHTML = tex_col2 ;
        new_row_children[2].innerHTML = tex_col3 ;
        new_row_children[3].innerHTML = tex_col4 ;
        tbl.appendChild( new_row ) ;
    }
    tbl.firstElementChild.remove() ;
}

// --- Quand la page HTML est prete
$(document).ready(function() {

    // -- Init
    gv_un1 = location.search.split('usrun=')[1] ;
    gv_un = gv_un1.split('&')[0] ;
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
    gv_nbartic = 0 ;
    gv_nbartictotal = "0" ;

    // -- Recup articles
    $.getJSON(url="./getlstartic", data={"usrun":gv_un , "nbdays":"10"}, success=function( data2 )
    {
        gv_nbartic = data2.length ;
        updateNbArtic() ;
        fillGUI(data2) ;
    }) ;

    // -- Recup nb articles
    $.getJSON(url="./getusrstt", data={"usrun":gv_un}, success=function( data3 )
    {
        gv_nbartictotal = data3['nbarticles'] ;
        updateNbArtic() ;
    }) ;

} ) ;
