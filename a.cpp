#include <bits/stdc++.h>
using namespace std;
#define int long long
int mod = 1e9 + 7, mod1 = 998244353;
#define vi vector<int>
template <typename T> istream& operator>>(istream& in, vector<T>& a) {
    for (auto& x : a)
        in >> x;
    return in;
}
template <typename T> ostream& operator<<(ostream& out, vector<T>& a) {
    for (auto& x : a)
        out << x << " ";
    return out;
}
template <typename T, typename K>
istream& operator>>(istream& in, pair<T, K>& a) {
    in >> a.F >> a.S;
    return in;
}
template <typename T, typename K>
ostream& operator<<(ostream& out, pair<T, K>& a) {
    out << a.F << " " << a.S;
    return out;
}

int modadd(int a, int b, int zz) { return ((a % zz) + (b % zz)) % zz; }
int modmul(int a, int b, int zz) { return ((a % zz) * (b % zz)) % zz; }
int modexp(int a, int b, int zz) {
    int ans = 1;
    while (b > 0) {
        if (b & 1)
            ans = modmul(ans, a, zz);
        a = modmul(a, a, zz);
        b >>= 1;
    }
    return ans;
}
int modinv(int a, int zz) { return modexp(a, zz - 2, zz); }
int moddiv(int a, int b, int zz) { return modmul(a, modinv(b, zz), zz); }
int binexp(int a, int b) {
    a %= mod;
    int res = 1;
    while (b > 0) {
        if (b & 1)
            res = (res * a) % mod;
        a = (a * a) % mod;
        b >>= 1;
    }
    return res;
}
void solve() {
    int n;
    cin >> n;
    string s;
    cin >> s;
    int sum = 0;
    vector<int> arr(n);
    vector<int> temp;
    for (int i = 0; i < n; i++) {
        if(s[i]=='0'){
            if(!temp.empty() && temp.back()+1==i)
            {
                cout<<-1<<endl;
                    return ;
            }
              temp.push_back(i);
            
        }
    }
    int m=temp.begin();
    int l=0;
    for(int i=0;i<m;i++)
        {
            int r=temp[i];
            for(int j=l;j<=r;j++)
                {
                    
                }
            l=r+1;
        }
    int r=n-1;
    if(l!=r)
    {
        for(int i=l;i<=r;i++)
            {
                
            }
    } 
    int ans=0;
    for (int i = 0; i < n; i++) {
       ans=max(ans,abs(arr[i]));
    }
    cout << ans<<endl;
}
signed main() {
    ios::sync_with_stdio(false);
    cin.tie(NULL);
    cout.tie(NULL);
    int t;
    cin >> t;
    while (t--) {
        solve();
    }

    return 0;
}
