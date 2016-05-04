import React from 'react';
const SearchBar = React.createClass({
    _onClick(event) {
        event.preventDefault();
        let query = $('.search-input').val();
        if (query) {
            window.location.href = window.location.origin+'/books?type=free&q='+query;
        }
    },
    render() {
        return(<div className="col-lg-6 search-elements">
                <form onSubmit={this._onClick}>
                    <div className="form-group has-feedback">
                        <input className="search-input form-control" type="text" placeholder="What do you want to read today?" value={this.props.query} />
                        <i className="glyphicon glyphicon-search form-control-feedback"></i>
                    </div>
                </form>
            </div>);
    }
});

export default SearchBar;
